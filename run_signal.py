"""Send an approval/rejection Signal to a running RTLDebugWorkflow.

Usage:
    # approve
    python run_signal.py rtl-debug-counter_bug approve

    # reject with a comment
    python run_signal.py rtl-debug-counter_bug reject --comment "Patch looks wrong"
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from temporalio.client import Client

from app.config import config
from app.models import ApprovalSignal, ApprovalStatus
from app.workflows import RTLDebugWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(workflow_id: str, decision: ApprovalStatus, comment: str) -> None:
    client = await Client.connect(
        config.temporal_host,
        namespace=config.temporal_namespace,
    )

    handle = client.get_workflow_handle_for(
        RTLDebugWorkflow.run,
        workflow_id=workflow_id,
    )

    signal = ApprovalSignal(decision=decision, comment=comment)
    await handle.signal(RTLDebugWorkflow.submit_approval, signal)

    logger.info(
        "Signal sent – workflow_id=%s  decision=%s",
        workflow_id,
        decision.value,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send approval signal to RTLDebugWorkflow")
    parser.add_argument("workflow_id", help="Temporal workflow ID")
    parser.add_argument(
        "decision",
        choices=["approve", "reject"],
        help="Human decision on the proposed patch",
    )
    parser.add_argument("--comment", default="", help="Optional comment")
    args = parser.parse_args()

    decision_enum = (
        ApprovalStatus.approved if args.decision == "approve" else ApprovalStatus.rejected
    )
    asyncio.run(main(args.workflow_id, decision_enum, args.comment))
