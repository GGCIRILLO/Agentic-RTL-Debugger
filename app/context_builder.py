"""Build a compact RTL context string for the LLM prompt.

Selects the lines surrounding the suspected failure locations.
This module will be called by the build_context Activity in Phase 4.
"""

from __future__ import annotations

from app.models import CaseFiles, FailureSummary

_WINDOW = 8  # lines of context around each suspected line


def build_context(case_files: CaseFiles, failure: FailureSummary) -> str:
    """Return a focused RTL snippet centred on the suspected buggy lines.

    Args:
        case_files: The bundle containing the original RTL source code.
        failure: The summary containing suspected line numbers.

    Returns:
        A string containing a window of lines around the suspected errors, 
        prefixed with line numbers. If no lines are suspected or if all 
        suspected lines are out of bounds, the full RTL source is returned.
    """
    if not failure.suspected_lines:
        # Fallback: return the full RTL (it's a small demo file)
        return case_files.rtl_source

    rtl_lines = case_files.rtl_source.splitlines()
    total = len(rtl_lines)

    selected_indices: set[int] = set()
    for lineno in failure.suspected_lines:
        # Convert 1-based line number to 0-based index
        idx = lineno - 1
        for i in range(max(0, idx - _WINDOW), min(total, idx + _WINDOW + 1)):
            selected_indices.add(i)

    if not selected_indices:
        return case_files.rtl_source

    snippet_lines = []
    prev: int | None = None
    for i in sorted(selected_indices):
        if prev is not None and i - prev > 1:
            snippet_lines.append("...")
        snippet_lines.append(f"{i + 1:4d}  {rtl_lines[i]}")
        prev = i

    return "\n".join(snippet_lines)
