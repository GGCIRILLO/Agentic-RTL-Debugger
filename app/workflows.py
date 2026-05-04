"""RTLDebugWorkflow – main Temporal workflow.

Follows Temporal Python SDK >=1.7 conventions:
- @workflow.defn / @workflow.run
- workflow.execute_activity for Activities
- workflow.wait_condition + signal handler for human-in-the-loop
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities (referenced by name at registration time to avoid
# importing non-deterministic I/O code inside the workflow sandbox).
with workflow.unsafe.imports_not_sandboxed():
    from app.models import (
        ApprovalSignal,
        ApprovalStatus,
        CaseFiles,
        DebugReport,
        FailureSummary,
        PatchProposal,
        RootCauseAnalysis,
        SimulationResult,
        WorkflowStatus,
    )
    from app.activities import (
        load_case_files,
        run_compile,
        run_simulation,
        parse_simulation_log,
        build_context,
        generate_root_cause,
        generate_patch,
        apply_patch,
        rerun_simulation,
        save_report,
    )

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry policy used for all Activities
# ---------------------------------------------------------------------------
_DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
)


@workflow.defn
class RTLDebugWorkflow:
    """Orchestrates the full RTL debug loop for a given case_id."""

    def __init__(self) -> None:
        self._status: WorkflowStatus = WorkflowStatus.started
        self._approval: Optional[ApprovalSignal] = None
        self._report: Optional[DebugReport] = None

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    @workflow.signal
    async def submit_approval(self, signal: ApprovalSignal) -> None:
        """Human-in-the-loop signal: approve or reject the proposed patch."""
        logger.info("Approval signal received: %s", signal.decision)
        self._approval = signal

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @workflow.query
    def get_status(self) -> str:
        return self._status.value

    @workflow.query
    def get_report(self) -> Optional[dict]:
        return self._report.model_dump() if self._report else None

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    @workflow.run
    async def run(self, case_id: str) -> dict:
        workflow_id = workflow.info().workflow_id
        logger.info("RTLDebugWorkflow started – case_id=%s workflow_id=%s", case_id, workflow_id)

        report = DebugReport(
            case_id=case_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.started,
        )

        try:
            # ----------------------------------------------------------------
            # Step 1 – Load source files
            # ----------------------------------------------------------------
            case_files: CaseFiles = await workflow.execute_activity(
                load_case_files,
                case_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DEFAULT_RETRY,
            )

            # ----------------------------------------------------------------
            # Step 2 – Compile
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.simulating
            compile_result: SimulationResult = await workflow.execute_activity(
                run_compile,
                case_files,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_DEFAULT_RETRY,
            )

            if not compile_result.compiled:
                report.status = WorkflowStatus.failed
                report.failure_summary = FailureSummary(
                    raw_failure=compile_result.compile_log,
                    failure_type="compile_error",
                )
                self._report = report
                await workflow.execute_activity(
                    save_report,
                    report,
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return report.model_dump()

            # ----------------------------------------------------------------
            # Step 3 – Simulate
            # ----------------------------------------------------------------
            sim_result: SimulationResult = await workflow.execute_activity(
                run_simulation,
                case_files,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_DEFAULT_RETRY,
            )

            if sim_result.simulation_passed:
                report.status = WorkflowStatus.completed
                report.rerun_result = sim_result
                self._report = report
                await workflow.execute_activity(
                    save_report,
                    report,
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return report.model_dump()

            # ----------------------------------------------------------------
            # Step 4 – Parse failure
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.parsing
            failure: FailureSummary = await workflow.execute_activity(
                parse_simulation_log,
                sim_result,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DEFAULT_RETRY,
            )
            report.failure_summary = failure

            # ----------------------------------------------------------------
            # Step 5 – Build context
            # ----------------------------------------------------------------
            context: str = await workflow.execute_activity(
                build_context,
                (case_files, failure),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DEFAULT_RETRY,
            )

            # ----------------------------------------------------------------
            # Step 6 – LLM: root cause analysis
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.analyzing
            root_cause: RootCauseAnalysis = await workflow.execute_activity(
                generate_root_cause,
                (case_files, failure, context),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=_DEFAULT_RETRY,
            )
            report.root_cause = root_cause

            # ----------------------------------------------------------------
            # Step 7 – LLM: patch proposal
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.proposing_patch
            patch: PatchProposal = await workflow.execute_activity(
                generate_patch,
                (case_files, root_cause),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=_DEFAULT_RETRY,
            )
            report.proposed_patch = patch

            # ----------------------------------------------------------------
            # Step 8 – Wait for human approval (Signal)
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.awaiting_approval
            logger.info("Workflow paused – waiting for approval signal")

            # Wait up to 24 h for a human decision
            await workflow.wait_condition(
                lambda: self._approval is not None,
                timeout=timedelta(hours=24),
            )

            if self._approval is None or self._approval.decision == ApprovalStatus.rejected:
                report.approval_status = ApprovalStatus.rejected
                report.status = WorkflowStatus.completed
                self._report = report
                await workflow.execute_activity(
                    save_report,
                    report,
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return report.model_dump()

            report.approval_status = ApprovalStatus.approved

            # ----------------------------------------------------------------
            # Step 9 – Apply patch
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.applying_patch
            await workflow.execute_activity(
                apply_patch,
                (case_files, patch),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_DEFAULT_RETRY,
            )

            # ----------------------------------------------------------------
            # Step 10 – Rerun simulation on patched file
            # ----------------------------------------------------------------
            self._status = WorkflowStatus.rerunning
            rerun: SimulationResult = await workflow.execute_activity(
                rerun_simulation,
                case_files,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_DEFAULT_RETRY,
            )
            report.rerun_result = rerun
            report.status = WorkflowStatus.completed

        except Exception as exc:  # noqa: BLE001
            logger.exception("Workflow failed with exception: %s", exc)
            report.status = WorkflowStatus.failed

        # ----------------------------------------------------------------
        # Step 11 – Save final report
        # ----------------------------------------------------------------
        self._report = report
        await workflow.execute_activity(
            save_report,
            report,
            start_to_close_timeout=timedelta(seconds=30),
        )
        return report.model_dump()
