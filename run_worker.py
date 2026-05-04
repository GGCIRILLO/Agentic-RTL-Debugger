"""Start the Temporal worker and register the workflow + all activities.

Usage:
    python run_worker.py
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import config
from app.workflows import RTLDebugWorkflow
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    client = await Client.connect(
        config.temporal_host,
        namespace=config.temporal_namespace,
    )
    logger.info(
        "Connected to Temporal at %s (namespace=%s)",
        config.temporal_host,
        config.temporal_namespace,
    )

    worker = Worker(
        client,
        task_queue=config.task_queue,
        workflows=[RTLDebugWorkflow],
        activities=[
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
        ],
    )

    logger.info("Worker listening on task queue '%s'", config.task_queue)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
