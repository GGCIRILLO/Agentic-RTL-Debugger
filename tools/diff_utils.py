"""Unified diff utilities."""

from __future__ import annotations

import difflib


def unified_diff(original: str, patched: str, filename: str = "module.v") -> str:
    """Return a unified diff string between two Verilog source strings."""
    a_lines = original.splitlines(keepends=True)
    b_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(
        a_lines,
        b_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)
