"""Launch a new RTLDebugWorkflow execution for a given case_id.

Usage:
    python run_starter.py counter_bug
    python run_starter.py counter_bug --workflow-id my-custom-id
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from temporalio.client import Client

from app.config import config
from app.workflows import RTLDebugWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(case_id: str, workflow_id: str) -> None:
    client = await Client.connect(
        config.temporal_host,
        namespace=config.temporal_namespace,
    )

    handle = await client.start_workflow(
        RTLDebugWorkflow.run,
        case_id,
        id=workflow_id,
        task_queue=config.task_queue,
    )

    logger.info(
        "Workflow started: workflow_id=%s  run_id=%s",
        handle.id,
        handle.first_execution_run_id,
    )
    logger.info("Monitor in the Temporal Web UI: http://localhost:8233")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start RTLDebugWorkflow")
    parser.add_argument("case_id", help="Identifier of the debug case (e.g. counter_bug)")
    parser.add_argument(
        "--workflow-id",
        default=None,
        help="Custom workflow ID (defaults to rtl-debug-<case_id>)",
    )
    args = parser.parse_args()
    wf_id = args.workflow_id or f"rtl-debug-{args.case_id}"
    asyncio.run(main(args.case_id, wf_id))
