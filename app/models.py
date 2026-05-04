"""Pydantic data models shared across workflow and activities."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class WorkflowStatus(str, Enum):
    started = "started"
    simulating = "simulating"
    parsing = "parsing"
    analyzing = "analyzing"
    proposing_patch = "proposing_patch"
    awaiting_approval = "awaiting_approval"
    applying_patch = "applying_patch"
    rerunning = "rerunning"
    completed = "completed"
    failed = "failed"


class CaseFiles(BaseModel):
    """All source files for a debug case."""

    case_id: str
    spec: str = Field(description="Textual specification")
    rtl_source: str = Field(description="Verilog RTL source code")
    testbench: str = Field(description="Verilog testbench source code")
    rtl_filename: str
    tb_filename: str


class SimulationResult(BaseModel):
    compiled: bool
    compile_log: str = ""
    simulation_passed: bool = False
    simulation_log: str = ""
    log_path: str = ""


class FailureSummary(BaseModel):
    raw_failure: str
    suspected_module: str = ""
    suspected_lines: list[int] = Field(default_factory=list)
    failure_type: str = ""


class RootCauseAnalysis(BaseModel):
    summary: str
    suspected_module: str
    suspected_lines: list[int] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    explanation: str = ""


class PatchProposal(BaseModel):
    original_snippet: str
    patched_snippet: str
    explanation: str
    diff: str = ""


class ApprovalSignal(BaseModel):
    decision: ApprovalStatus
    comment: str = ""


class DebugIteration(BaseModel):
    patch: PatchProposal
    approval_status: ApprovalStatus
    rerun_result: Optional[SimulationResult] = None


class DebugReport(BaseModel):
    """Final report persisted after workflow completes."""

    case_id: str
    workflow_id: str
    status: WorkflowStatus
    failure_summary: Optional[FailureSummary] = None
    root_cause: Optional[RootCauseAnalysis] = None
    proposed_patch: Optional[PatchProposal] = None
    approval_status: ApprovalStatus = ApprovalStatus.pending
    rerun_result: Optional[SimulationResult] = None
    history: list[DebugIteration] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Debug Report – `{self.case_id}`",
            f"**Workflow ID**: `{self.workflow_id}`",
            f"**Status**: {self.status.value}",
            "",
        ]
        if self.failure_summary:
            lines += [
                "## Failure Summary",
                f"- Module: `{self.failure_summary.suspected_module}`",
                f"- Lines: {self.failure_summary.suspected_lines}",
                f"- Type: {self.failure_summary.failure_type}",
                f"```\n{self.failure_summary.raw_failure}\n```",
                "",
            ]
        if self.root_cause:
            lines += [
                "## Root Cause Analysis",
                f"- Confidence: {self.root_cause.confidence:.0%}",
                f"{self.root_cause.summary}",
                f"{self.root_cause.explanation}",
                "",
            ]
        
        for i, it in enumerate(self.history):
            lines += [
                f"## Iteration {i+1} (Failed)",
                it.patch.explanation,
                f"```diff\n{it.patch.diff}\n```",
                f"**Approval**: {it.approval_status.value}",
            ]
            if it.rerun_result:
                outcome = "✅ PASSED" if it.rerun_result.simulation_passed else "❌ FAILED"
                lines += [f"**Rerun Result**: {outcome}", ""]

        if self.proposed_patch:
            lines += [
                "## Proposed Patch",
                self.proposed_patch.explanation,
                f"```diff\n{self.proposed_patch.diff}\n```",
                f"**Approval**: {self.approval_status.value}",
                "",
            ]
        if self.rerun_result:
            outcome = "✅ PASSED" if self.rerun_result.simulation_passed else "❌ FAILED"
            lines += ["## Rerun Result", outcome, ""]
        return "\n".join(lines)
