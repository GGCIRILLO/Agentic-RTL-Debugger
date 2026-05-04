"""Temporal Activities for RTLDebugWorkflow.

All I/O, subprocess calls, and LLM calls live here – never in the Workflow.
Each activity is a plain async function decorated with @activity.defn.

At this stage (Phase 2) the bodies are stubs that will be filled in
Phases 3-7.  Each stub raises NotImplementedError so tests clearly fail
until the implementation is added.
"""

from __future__ import annotations

import logging

from temporalio import activity

from app.models import (
    CaseFiles,
    FailureSummary,
    PatchProposal,
    RootCauseAnalysis,
    SimulationResult,
    DebugReport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 3: File loading & simulation
# ---------------------------------------------------------------------------


@activity.defn
async def load_case_files(case_id: str) -> CaseFiles:
    """Read spec, RTL and testbench from cases/<case_id>/."""
    raise NotImplementedError("load_case_files – implement in Phase 3")


@activity.defn
async def run_compile(case_files: CaseFiles) -> SimulationResult:
    """Invoke iverilog to compile the Verilog design and testbench."""
    raise NotImplementedError("run_compile – implement in Phase 3")


@activity.defn
async def run_simulation(case_files: CaseFiles) -> SimulationResult:
    """Run vvp on the compiled binary and capture the simulation log."""
    raise NotImplementedError("run_simulation – implement in Phase 3")


# ---------------------------------------------------------------------------
# Phase 4: Parsing & context
# ---------------------------------------------------------------------------


@activity.defn
async def parse_simulation_log(sim_result: SimulationResult) -> FailureSummary:
    """Extract the primary failure from the simulation log."""
    raise NotImplementedError("parse_simulation_log – implement in Phase 4")


@activity.defn
async def build_context(args: tuple[CaseFiles, FailureSummary]) -> str:
    """Select the relevant RTL fragments and return a compact context string."""
    raise NotImplementedError("build_context – implement in Phase 4")


# ---------------------------------------------------------------------------
# Phase 5: LLM integration
# ---------------------------------------------------------------------------


@activity.defn
async def generate_root_cause(
    args: tuple[CaseFiles, FailureSummary, str]
) -> RootCauseAnalysis:
    """Ask the LLM for a structured root cause diagnosis."""
    raise NotImplementedError("generate_root_cause – implement in Phase 5")


@activity.defn
async def generate_patch(
    args: tuple[CaseFiles, RootCauseAnalysis]
) -> PatchProposal:
    """Ask the LLM for a minimal patch proposal."""
    raise NotImplementedError("generate_patch – implement in Phase 5")


# ---------------------------------------------------------------------------
# Phase 6/7: Patch application & rerun
# ---------------------------------------------------------------------------


@activity.defn
async def apply_patch(args: tuple[CaseFiles, PatchProposal]) -> None:
    """Write the patched RTL file to outputs/patched/."""
    raise NotImplementedError("apply_patch – implement in Phase 7")


@activity.defn
async def rerun_simulation(case_files: CaseFiles) -> SimulationResult:
    """Compile and simulate the patched file."""
    raise NotImplementedError("rerun_simulation – implement in Phase 7")


@activity.defn
async def save_report(report: DebugReport) -> None:
    """Persist the DebugReport as JSON and Markdown under outputs/reports/."""
    raise NotImplementedError("save_report – implement in Phase 7")
