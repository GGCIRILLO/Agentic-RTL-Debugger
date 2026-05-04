"""Temporal Activities for RTLDebugWorkflow.

All I/O, subprocess calls, and LLM calls live here — never in the Workflow.
Each activity is a plain async function decorated with @activity.defn.

Implementation status:
  Phase 3 — DONE : load_case_files, run_compile, run_simulation
  Phase 4 — DONE : parse_simulation_log, build_context
  Phase 5 — DONE : generate_root_cause, generate_patch
  Phase 7 — DONE : apply_patch, rerun_simulation, save_report
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from temporalio import activity

from app.config import config
from app.context_builder import build_context as _build_context
from app.llm_client import LLMClient
from app.log_parser import parse_log
from app.models import (
    CaseFiles,
    DebugReport,
    FailureSummary,
    PatchProposal,
    RootCauseAnalysis,
    SimulationResult,
)
from app.patcher import apply_patch as _apply_patch
from app.prompts import patch_proposal_prompt, root_cause_prompt
from tools.diff_utils import unified_diff
from tools.file_reader import load_case
from tools.simulation import compile_verilog, run_vvp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log_path(case_id: str, suffix: str) -> Path:
    """Return a path inside outputs/logs/, creating it if needed."""
    logs_dir = Path(config.outputs_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / f"{case_id}_{suffix}.log"


# ---------------------------------------------------------------------------
# Phase 3: File loading & simulation
# ---------------------------------------------------------------------------


@activity.defn
async def load_case_files(case_id: str) -> CaseFiles:
    """Read spec, RTL and testbench from cases/[case_id]/

    Args:
        case_id: The unique identifier for the debug case (e.g., 'counter_bug').

    Returns:
        A CaseFiles object containing the source code and metadata for the case.

    Raises:
        FileNotFoundError: If the case directory or required files are missing.
    """
    logger.info("Loading case files for case_id=%s", case_id)
    case_files = load_case(case_id)
    logger.info(
        "Loaded case_id=%s  rtl=%s  tb=%s",
        case_id, case_files.rtl_filename, case_files.tb_filename,
    )
    return case_files


@activity.defn
async def run_compile(case_files: CaseFiles) -> SimulationResult:
    """Compile RTL + testbench with iverilog.

    Args:
        case_files: The bundle of source files to compile.

    Returns:
        A SimulationResult containing the compilation success status and logs.
        The logs are also persisted to outputs/logs/.
    """
    logger.info("Compiling case_id=%s", case_files.case_id)

    case_dir    = Path(config.cases_dir).resolve() / case_files.case_id
    rtl_path    = case_dir / case_files.rtl_filename
    tb_path     = case_dir / case_files.tb_filename
    tmp_dir     = Path(tempfile.gettempdir()) / "rtl_debugger" / case_files.case_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    binary_path = tmp_dir / "sim.out"

    success, compile_log = await compile_verilog(rtl_path, tb_path, binary_path)

    log_file = _log_path(case_files.case_id, "compile")
    log_file.write_text(compile_log)
    logger.info("Compile log saved to %s", log_file)

    if not success:
        logger.warning("Compilation FAILED for case_id=%s", case_files.case_id)

    return SimulationResult(
        compiled=success,
        compile_log=compile_log,
        log_path=str(binary_path),
    )


@activity.defn
async def run_simulation(case_files: CaseFiles) -> SimulationResult:
    """Run the compiled binary with vvp and capture the simulation log.

    Args:
        case_files: The case metadata (used for log path resolution).

    Returns:
        A SimulationResult containing the simulation pass/fail status and output log.
        The log is also persisted to outputs/logs/.

    Raises:
        FileNotFoundError: If the compiled binary (sim.out) does not exist.
    """
    logger.info("Running simulation for case_id=%s", case_files.case_id)

    tmp_dir     = (Path(tempfile.gettempdir()) / "rtl_debugger" / case_files.case_id).resolve()
    binary_path = tmp_dir / "sim.out"

    if not binary_path.exists():
        raise FileNotFoundError(
            f"Compiled binary not found at {binary_path}. "
            "Ensure run_compile succeeded before calling run_simulation."
        )

    simulation_passed, simulation_log = await run_vvp(binary_path)

    log_file = _log_path(case_files.case_id, "simulation")
    log_file.write_text(simulation_log)
    logger.info("Simulation log saved to %s", log_file)

    if not simulation_passed:
        logger.warning("Simulation FAILED for case_id=%s", case_files.case_id)

    return SimulationResult(
        compiled=True,
        simulation_passed=simulation_passed,
        simulation_log=simulation_log,
        log_path=str(log_file),
    )


# ---------------------------------------------------------------------------
# Phase 4: Parsing & context
# ---------------------------------------------------------------------------


@activity.defn
async def parse_simulation_log(sim_result: SimulationResult) -> FailureSummary:
    """Extract the primary failure from the simulation log using regex patterns.

    Args:
        sim_result: The result containing the raw simulation log string.

    Returns:
        A FailureSummary with structured data about the suspected bug (module, lines, type).
    """
    logger.info(
        "Parsing simulation log (%d chars)", len(sim_result.simulation_log)
    )
    failure = parse_log(sim_result.simulation_log)
    logger.info(
        "Parsed failure: type=%s  module=%s  lines=%s",
        failure.failure_type, failure.suspected_module, failure.suspected_lines,
    )
    return failure


@activity.defn
async def build_context(args: tuple[CaseFiles, FailureSummary]) -> str:
    """Select the relevant RTL fragments surrounding suspected lines.

    Args:
        args: A tuple containing (CaseFiles, FailureSummary).

    Returns:
        A string containing numbered RTL source lines ±8 lines around the failures.
        If no lines were suspected, returns the full RTL source.
    """
    case_files, failure = args
    logger.info(
        "Building context for case_id=%s  suspected_lines=%s",
        case_files.case_id, failure.suspected_lines,
    )
    context = _build_context(case_files, failure)
    logger.info(
        "Context built: %d lines / %d chars",
        context.count("\n") + 1, len(context),
    )
    return context


# ---------------------------------------------------------------------------
# Phase 5: LLM integration
# ---------------------------------------------------------------------------


@activity.defn
async def generate_root_cause(
    args: tuple[CaseFiles, FailureSummary, str],
) -> RootCauseAnalysis:
    """Ask the LLM for a structured root cause diagnosis.

    Calls the LLM with the root_cause_prompt template and parses the
    JSON response into a RootCauseAnalysis model.  The LLMClient's
    _parse_json() handles markdown fences and leading prose that local
    models sometimes emit before the JSON block.

    If the model returns malformed JSON after all extraction attempts,
    ValueError is raised and Temporal retries the activity according to
    the configured retry policy (max 3 attempts, exponential backoff).
    """
    case_files, failure, context = args
    logger.info(
        "Generating root cause for case_id=%s via provider=%s model=%s",
        case_files.case_id, config.llm_provider, config.llm_model,
    )

    client   = LLMClient()
    messages = root_cause_prompt(case_files, failure, context)
    data     = await client.chat(messages)

    # Validate and coerce into the typed model.
    # model_validate() raises ValidationError (subclass of ValueError) on
    # schema mismatch, which Temporal treats as a retryable application error.
    rca = RootCauseAnalysis.model_validate(data)

    logger.info(
        "Root cause: summary=%r  confidence=%.2f  lines=%s",
        rca.summary, rca.confidence, rca.suspected_lines,
    )
    return rca


@activity.defn
async def generate_patch(
    args: tuple[CaseFiles, RootCauseAnalysis, SimulationResult, PatchProposal | None, str],
) -> PatchProposal:
    """Ask the LLM for a correct patch proposal.

    Receives the full CaseFiles (spec + RTL + testbench), the structured
    root cause, and the raw SimulationResult so the LLM can reason about
    both the intended behaviour (spec) and the exact failure messages.

    The same JSON robustness strategy used in generate_root_cause applies:
    malformed output raises ValueError → Temporal retries the activity.
    """
    case_files, root_cause, sim_result, prev_patch, rerun_log = args
    logger.info(
        "Generating patch for case_id=%s via provider=%s model=%s",
        case_files.case_id, config.llm_provider, config.llm_model,
    )

    client   = LLMClient()
    messages = patch_proposal_prompt(
        case_files,
        root_cause,
        sim_result_log=sim_result.simulation_log or "",
        previous_patch=prev_patch,
        rerun_log=rerun_log,
    )
    data     = await client.chat(messages)

    patch = PatchProposal.model_validate(data)

    # Pre-calculate diff and validate patch applicability
    try:
        patched_source = _apply_patch(case_files, patch)
        patch.diff = unified_diff(
            case_files.rtl_source,
            patched_source,
            case_files.rtl_filename,
        )
    except Exception as exc:
        logger.warning("Could not apply LLM patch: %s", exc)
        raise ValueError(f"Invalid patch proposal: {exc}")

    logger.info(
        "Patch proposal: explanation=%r",
        patch.explanation,
    )
    return patch


# ---------------------------------------------------------------------------
# Phase 7: Patch application & rerun
# ---------------------------------------------------------------------------


@activity.defn
async def apply_patch(args: tuple[CaseFiles, PatchProposal]) -> None:
    """Write the patched RTL file to outputs/patched/.

    Args:
        args: A tuple containing (CaseFiles, PatchProposal).

    Returns:
        None. Side effect: creates a file in outputs/patched/<case_id>/.
    """
    case_files, patch = args
    logger.info("Applying patch for case_id=%s", case_files.case_id)

    patched_source = _apply_patch(case_files, patch)

    # Generate the diff and store it in the proposal so it appears in the report
    patch.diff = unified_diff(
        case_files.rtl_source,
        patched_source,
        case_files.rtl_filename,
    )

    patched_dir = Path(config.outputs_dir) / "patched" / case_files.case_id
    patched_dir.mkdir(parents=True, exist_ok=True)
    patched_file = patched_dir / case_files.rtl_filename

    patched_file.write_text(patched_source)
    logger.info("Patched RTL saved to %s", patched_file)


@activity.defn
async def rerun_simulation(case_files: CaseFiles) -> SimulationResult:
    """Compile and simulate the patched RTL file to verify the fix.

    Uses the patched RTL from outputs/patched/ but the original testbench.

    Args:
        case_files: The original case metadata.

    Returns:
        A SimulationResult containing the rerun success status and logs.
    """
    case_id = case_files.case_id
    logger.info("Rerunning simulation with patch for case_id=%s", case_id)

    # Paths
    patched_dir  = (Path(config.outputs_dir) / "patched" / case_id).resolve()
    rtl_path     = patched_dir / case_files.rtl_filename
    tb_path      = (Path(config.cases_dir) / case_id / case_files.tb_filename).resolve()

    if not rtl_path.exists():
        raise FileNotFoundError(f"Patched RTL not found at {rtl_path}")

    # Binary path
    tmp_dir = Path(tempfile.gettempdir()) / "rtl_debugger" / case_id / "patched"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    binary_path = tmp_dir / "sim.out"

    # Compile
    success, compile_log = await compile_verilog(rtl_path, tb_path, binary_path)
    log_file_c = _log_path(case_id, "patch_compile")
    log_file_c.write_text(compile_log)

    if not success:
        logger.warning("Rerun: compilation FAILED for case_id=%s", case_id)
        return SimulationResult(compiled=False, compile_log=compile_log)

    # Simulate
    sim_passed, sim_log = await run_vvp(binary_path)
    log_file_s = _log_path(case_id, "patch_simulation")
    log_file_s.write_text(sim_log)

    if sim_passed:
        logger.info("Rerun: simulation PASSED for case_id=%s", case_id)
    else:
        logger.warning("Rerun: simulation FAILED for case_id=%s", case_id)

    return SimulationResult(
        compiled=True,
        simulation_passed=sim_passed,
        simulation_log=sim_log,
        log_path=str(log_file_s),
    )


@activity.defn
async def save_report(report: DebugReport) -> None:
    """Persist the final DebugReport as JSON and Markdown under outputs/reports/.

    Args:
        report: The full aggregated DebugReport object.

    Returns:
        None. Side effect: creates two files in outputs/reports/.
    """
    logger.info("Saving report for case_id=%s", report.case_id)

    reports_dir = Path(config.outputs_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = reports_dir / f"{report.case_id}_report.json"
    json_path.write_text(report.model_dump_json(indent=2))

    # Markdown
    md_path = reports_dir / f"{report.case_id}_report.md"
    md_path.write_text(report.to_markdown())

    logger.info("Reports saved to %s and %s", json_path, md_path)
