"""Utilities for parsing Icarus Verilog simulation output logs.

This module will be called by the parse_simulation_log Activity in Phase 4.
"""

from __future__ import annotations

import re
from app.models import FailureSummary


# Patterns covering common VCD/vvp failure formats
_ERROR_PATTERNS = [
    (re.compile(r"ERROR:?\s*(?P<msg>.+)", re.IGNORECASE), "ERROR"),
    (re.compile(r"ASSERTION FAILED:?\s*(?P<msg>.+)", re.IGNORECASE), "ASSERTION FAILED"),
    (re.compile(r"MISMATCH:?\s*(?P<msg>.+)", re.IGNORECASE), "MISMATCH"),
    (re.compile(r"FAILED:?\s*(?P<msg>.+)", re.IGNORECASE), "FAILED"),
    (re.compile(r"(?P<msg>Expected .+, got .+)", re.IGNORECASE), "EXPECTED_GOT_MISMATCH"),
]

_FILE_LINE_RE = re.compile(r"(?P<file>[\w./]+\.v):(?P<line>\d+)")


def parse_log(simulation_log: str) -> FailureSummary:
    """Extract the primary failure from a vvp simulation log using regex matching.

    Args:
        simulation_log: The raw output log from the vvp simulation.

    Returns:
        A FailureSummary object containing the extracted error message, 
        the suspected file name, the suspected line numbers, and the failure type.
    """
    lines = simulation_log.splitlines()

    raw_failure_lines: list[str] = []
    suspected_lines: list[int] = []
    suspected_module = ""
    failure_type = ""

    for line in lines:
        if "$finish" in line or "$stop" in line:
            continue

        for pattern, ftype in _ERROR_PATTERNS:
            if pattern.search(line):
                raw_failure_lines.append(line)
                if not failure_type:
                    failure_type = ftype

        m = _FILE_LINE_RE.search(line)
        if m:
            if not suspected_module:
                suspected_module = m.group("file")
            suspected_lines.append(int(m.group("line")))

    raw_failure = "\n".join(raw_failure_lines) or simulation_log[:500]
    return FailureSummary(
        raw_failure=raw_failure,
        suspected_module=suspected_module,
        suspected_lines=list(dict.fromkeys(suspected_lines)),  # dedup, preserve order
        failure_type=failure_type or "simulation_failure",
    )
