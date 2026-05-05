"""Cases router: enumerate available debug cases and their RTL source files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import config

router = APIRouter(prefix="/api/cases", tags=["cases"])

CASES_DIR = Path(config.cases_dir)
REPORTS_DIR = Path(config.outputs_dir) / "reports"


def _extract_description(spec: str) -> str:
    """Extract the plain-text content under the '## Description' heading only."""
    match = re.search(r'##\s*Description\s*\n+([^#]+)', spec, re.DOTALL)
    if match:
        text = match.group(1).strip()
        # Drop markdown table rows and separator lines
        lines = [
            l for l in text.splitlines()
            if not l.strip().startswith('|') and not l.strip().startswith('---')
        ]
        return ' '.join(' '.join(lines).split())
    # Fallback: first non-heading paragraphs
    lines = [l.strip() for l in spec.splitlines() if l.strip() and not l.startswith('#')]
    return ' '.join(lines[:3]) if lines else ''


def _load_case_meta(case_dir: Path) -> dict:
    """Read metadata for a single case directory."""
    spec_file = case_dir / "spec.md"
    spec = spec_file.read_text() if spec_file.exists() else ""

    rtl_files = [f.name for f in case_dir.glob("*.v") if not f.name.startswith("tb_")]
    tb_files = [f.name for f in case_dir.glob("tb_*.v")]

    # Load last report if available
    report_path = REPORTS_DIR / f"{case_dir.name}_report.json"
    last_report = None
    if report_path.exists():
        try:
            last_report = json.loads(report_path.read_text())
        except Exception:
            pass

    return {
        "case_id": case_dir.name,
        "description": _extract_description(spec),
        "rtl_files": sorted(rtl_files),
        "tb_files": sorted(tb_files),
        "has_report": last_report is not None,
        "last_status": last_report.get("status") if last_report else None,
        "last_simulation_passed": (
            (last_report.get("rerun_result") or {}).get("simulation_passed")
            if last_report
            else None
        ),
    }


@router.get("")
async def list_cases():
    """Return all available debug cases with metadata."""
    if not CASES_DIR.exists():
        return []
    cases = []
    for d in sorted(CASES_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            cases.append(_load_case_meta(d))
    return cases


@router.get("/{case_id}")
async def get_case(case_id: str):
    """Return full source files for a specific case."""
    case_dir = CASES_DIR / case_id
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    meta = _load_case_meta(case_dir)

    # Add full source code
    rtl_sources = {}
    for f in case_dir.glob("*.v"):
        rtl_sources[f.name] = f.read_text()

    return {**meta, "sources": rtl_sources}


@router.get("/{case_id}/report")
async def get_report(case_id: str):
    """Return the last saved debug report for a case."""
    report_path = REPORTS_DIR / f"{case_id}_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"No report found for case '{case_id}'")
    return json.loads(report_path.read_text())
