"""Temporal Activities for RTLDebugWorkflow.

All I/O, subprocess calls, and LLM calls live here — never in the Workflow.
Each activity is a plain async function decorated with @activity.defn.

Implementation status:
  Phase 3 — DONE : load_case_files, run_compile, run_simulation
  Phase 4 — stub : parse_simulation_log, build_context
  Phase 5 — stub : generate_root_cause, generate_patch
  Phase 7 — stub : apply_patch, rerun_simulation, save_report
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from temporalio import activity

from app.config import config
from app.models import (
    CaseFiles,
    DebugReport,
    FailureSummary,
    PatchProposal,
    RootCauseAnalysis,
    SimulationResult,
)
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
    """Read spec, RTL and testbench from cases/<case_id>/.

    Delegates to tools.file_reader.load_case which validates the directory
    structure and raises FileNotFoundError on missing files.
    """
    logger.info("Loading case files for case_id=%s", case_id)
    case_files = load_case(case_id)
    logger.info(
        "Loaded case_id=%s  rtl=%s  tb=%s",
        case_id,
        case_files.rtl_filename,
        case_files.tb_filename,
    )
    return case_files


@activity.defn
async def run_compile(case_files: CaseFiles) -> SimulationResult:
    """Compile RTL + testbench with iverilog.

    Writes the compiled binary to a temp directory and persists the
    compile log to outputs/logs/<case_id>_compile.log.

    Returns a SimulationResult with compiled=True on success.
    The binary path is stored in log_path so downstream activities can
    locate it; the binary itself lives in the OS temp directory and is
    valid for the lifetime of the process.
    """
    logger.info("Compiling case_id=%s", case_files.case_id)

    case_dir = Path(config.cases_dir) / case_files.case_id
    rtl_path = case_dir / case_files.rtl_filename
    tb_path  = case_dir / case_files.tb_filename

    # Use a stable temp path so the binary can be found by run_simulation.
    tmp_dir = Path(tempfile.gettempdir()) / "rtl_debugger" / case_files.case_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    binary_path = tmp_dir / "sim.out"

    success, compile_log = await compile_verilog(rtl_path, tb_path, binary_path)

    # Persist compile log regardless of outcome.
    log_file = _log_path(case_files.case_id, "compile")
    log_file.write_text(compile_log)
    logger.info("Compile log saved to %s", log_file)

    if success:
        logger.info("Compilation succeeded for case_id=%s", case_files.case_id)
    else:
        logger.warning("Compilation FAILED for case_id=%s", case_files.case_id)

    return SimulationResult(
        compiled=success,
        compile_log=compile_log,
        # log_path carries the binary location so run_simulation can find it.
        log_path=str(binary_path),
    )


@activity.defn
async def run_simulation(case_files: CaseFiles) -> SimulationResult:
    """Run the compiled binary with vvp and capture the simulation log.

    Expects the binary to already exist at the path produced by run_compile.
    Persists the simulation log to outputs/logs/<case_id>_simulation.log.

    Returns a SimulationResult with simulation_passed=True when no failure
    keywords are found in the output and the process exits cleanly.
    """
    logger.info("Running simulation for case_id=%s", case_files.case_id)

    tmp_dir     = Path(tempfile.gettempdir()) / "rtl_debugger" / case_files.case_id
    binary_path = tmp_dir / "sim.out"

    if not binary_path.exists():
        raise FileNotFoundError(
            f"Compiled binary not found at {binary_path}. "
            "Ensure run_compile succeeded before calling run_simulation."
        )

    simulation_passed, simulation_log = await run_vvp(binary_path)

    # Persist simulation log.
    log_file = _log_path(case_files.case_id, "simulation")
    log_file.write_text(simulation_log)
    logger.info("Simulation log saved to %s", log_file)

    if simulation_passed:
        logger.info("Simulation PASSED for case_id=%s", case_files.case_id)
    else:
        logger.warning("Simulation FAILED for case_id=%s", case_files.case_id)

    return SimulationResult(
        compiled=True,
        simulation_passed=simulation_passed,
        simulation_log=simulation_log,
        log_path=str(log_file),
    )


# ---------------------------------------------------------------------------
# Phase 4: Parsing & context  (stubs)
# ---------------------------------------------------------------------------


@activity.defn
async def parse_simulation_log(sim_result: SimulationResult) -> FailureSummary:
    """Extract the primary failure from the simulation log."""
    raise NotImplementedError("parse_simulation_log — implement in Phase 4")


@activity.defn
async def build_context(args: tuple[CaseFiles, FailureSummary]) -> str:
    """Select the relevant RTL fragments and return a compact context string."""
    raise NotImplementedError("build_context — implement in Phase 4")


# ---------------------------------------------------------------------------
# Phase 5: LLM integration  (stubs)
# ---------------------------------------------------------------------------


@activity.defn
async def generate_root_cause(
    args: tuple[CaseFiles, FailureSummary, str],
) -> RootCauseAnalysis:
    """Ask the LLM for a structured root cause diagnosis."""
    raise NotImplementedError("generate_root_cause — implement in Phase 5")


@activity.defn
async def generate_patch(
    args: tuple[CaseFiles, RootCauseAnalysis],
) -> PatchProposal:
    """Ask the LLM for a minimal patch proposal."""
    raise NotImplementedError("generate_patch — implement in Phase 5")


# ---------------------------------------------------------------------------
# Phase 7: Patch application & rerun  (stubs)
# ---------------------------------------------------------------------------


@activity.defn
async def apply_patch(args: tuple[CaseFiles, PatchProposal]) -> None:
    """Write the patched RTL file to outputs/patched/."""
    raise NotImplementedError("apply_patch — implement in Phase 7")


@activity.defn
async def rerun_simulation(case_files: CaseFiles) -> SimulationResult:
    """Compile and simulate the patched file."""
    raise NotImplementedError("rerun_simulation — implement in Phase 7")


@activity.defn
async def save_report(report: DebugReport) -> None:
    """Persist the DebugReport as JSON and Markdown under outputs/reports/."""
    raise NotImplementedError("save_report — implement in Phase 7")
