"""Workflow management routes: start, status, signal (approve/reject), SSE stream."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.api.main import get_client
from app.config import config
from app.models import ApprovalSignal, ApprovalStatus
from app.workflows import RTLDebugWorkflow

router = APIRouter(prefix="/api/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)


# ── Request / Response schemas ─────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    decision: str  # "approved" | "rejected"
    comment: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────

def _wf_id(case_id: str) -> str:
    return f"rtl-debug-{case_id}"


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_workflows():
    """Return a list of all RTL-debug workflow executions (running + recent)."""
    client = get_client()
    results = []
    async for wf in client.list_workflows(query="WorkflowType='RTLDebugWorkflow'"):
        results.append({
            "workflow_id": wf.id,
            "run_id": wf.run_id,
            "status": wf.status.name if wf.status else "UNKNOWN",
            "start_time": wf.start_time.isoformat() if wf.start_time else None,
            "close_time": wf.close_time.isoformat() if wf.close_time else None,
        })
    return results


@router.post("/{case_id}/start")
async def start_workflow(case_id: str):
    """Start a new RTLDebugWorkflow for the given case_id."""
    client = get_client()
    wf_id = _wf_id(case_id)
    try:
        handle = await client.start_workflow(
            RTLDebugWorkflow.run,
            case_id,
            id=wf_id,
            task_queue=config.task_queue,
        )
        return {"workflow_id": wf_id, "run_id": handle.result_run_id}
    except WorkflowAlreadyStartedError:
        raise HTTPException(
            status_code=409,
            detail=f"Workflow '{wf_id}' is already running. Terminate it first or use a different case_id.",
        )


@router.get("/{workflow_id}/status")
async def get_status(workflow_id: str, run_id: str | None = None):
    """Query the current status and partial report.

    Running workflows → Temporal query.
    Closed workflows  → handle.describe() for true status + disk report for data.
    """
    client = get_client()
    handle = client.get_workflow_handle(workflow_id, run_id=run_id)

    # Temporal execution status → app status string
    _TMAP = {
        "RUNNING": None, "COMPLETED": "completed", "FAILED": "failed",
        "CANCELED": "terminated", "TERMINATED": "terminated",
        "TIMED_OUT": "failed", "CONTINUED_AS_NEW": "running",
    }

    # 1) Get true execution status first
    true_status = "failed"
    try:
        desc = await handle.describe()
        tname = desc.status.name if desc.status else None
        true_status = _TMAP.get(tname, "failed") if tname else "failed"
        if tname == "RUNNING":
            true_status = "running"
    except Exception:
        pass

    # 2) Use live query for both running and closed workflows! Temporal retains history
    # so we get the exact report for this run_id, not the last one from disk.
    try:
        status = await handle.query(RTLDebugWorkflow.get_status)
        report = await handle.query(RTLDebugWorkflow.get_report)
        return {
            "workflow_id": workflow_id,
            "status": status,
            "report": report,
            "execution_status": true_status
        }
    except Exception:
        pass

    # 3) Workflow is closed — load persisted report from disk for display data
    from pathlib import Path
    import json as _json
    from app.config import config as _cfg

    case_id = workflow_id.removeprefix("rtl-debug-")
    report_path = Path(_cfg.outputs_dir) / "reports" / f"{case_id}_report.json"
    disk_report: dict | None = None
    if report_path.exists():
        try:
            disk_report = _json.loads(report_path.read_text())
        except Exception:
            pass

    # Separate pipeline step from execution status
    pipe_status = disk_report.get("status", true_status) if disk_report else true_status
    return {
        "workflow_id": workflow_id,
        "status": pipe_status,
        "report": disk_report,
        "execution_status": true_status
    }


@router.post("/{workflow_id}/approve")
async def approve_patch(workflow_id: str, body: ApprovalRequest):
    """Send an approval or rejection signal to a waiting workflow."""
    client = get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        decision = ApprovalStatus(body.decision)
        signal = ApprovalSignal(decision=decision, comment=body.comment)
        await handle.signal(RTLDebugWorkflow.submit_approval, signal)
        return {"ok": True, "workflow_id": workflow_id, "decision": body.decision}
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{body.decision}'. Must be 'approved' or 'rejected'.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{workflow_id}/terminate")
async def terminate_workflow(workflow_id: str):
    """Terminate a running workflow (hard stop)."""
    client = get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.terminate(reason="Terminated via web UI")
        return {"ok": True, "workflow_id": workflow_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{workflow_id}/stream")
async def stream_status(workflow_id: str, run_id: str | None = None):
    """Server-Sent Events stream: pushes status + report updates every 1.5 s."""
    client = get_client()

    async def event_generator():
        handle = client.get_workflow_handle(workflow_id, run_id=run_id)
        prev_status = None
        prev_report_json = None

        # Send an immediate "connected" event
        yield f"data: {json.dumps({'event': 'connected', 'workflow_id': workflow_id})}\n\n"

        while True:
            try:
                desc = await handle.describe()
                tname = desc.status.name if desc.status else None
                is_running = tname == "RUNNING"
                
                # _TMAP is local to get_status, we need to redefine it or just map:
                _TMAP = {
                    "RUNNING": "running", "COMPLETED": "completed", "FAILED": "failed",
                    "CANCELED": "terminated", "TERMINATED": "terminated",
                    "TIMED_OUT": "failed", "CONTINUED_AS_NEW": "running",
                }
                true_status = _TMAP.get(tname, "failed") if tname else "failed"

                status = await handle.query(RTLDebugWorkflow.get_status)
                report = await handle.query(RTLDebugWorkflow.get_report)
                report_json = json.dumps(report, sort_keys=True)

                if status != prev_status or report_json != prev_report_json or not is_running:
                    payload = json.dumps({
                        "event": "update",
                        "workflow_id": workflow_id,
                        "status": status,
                        "report": report,
                        "execution_status": true_status
                    })
                    yield f"data: {payload}\n\n"
                    prev_status = status
                    prev_report_json = report_json

                if not is_running:
                    yield f"data: {json.dumps({'event': 'done', 'status': status})}\n\n"
                    break

            except Exception as exc:
                yield f"data: {json.dumps({'event': 'error', 'detail': str(exc)})}\n\n"
                break

            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
