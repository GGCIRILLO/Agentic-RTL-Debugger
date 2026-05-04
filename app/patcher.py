"""Apply a minimal patch to the RTL source file.

This module will be called by the apply_patch Activity in Phase 7.
"""

from __future__ import annotations
from app.models import CaseFiles, PatchProposal
import re

def _normalize(text: str) -> str:
    """Strip leading/trailing whitespace from each line, collapse blank lines."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def apply_patch(case_files: CaseFiles, patch: PatchProposal) -> str:
    """Replace the original snippet with the patched snippet in the RTL source.

    Args:
        case_files: The bundle containing the original RTL source code.
        patch: The proposal containing the original and patched snippets.

    Returns:
        The full patched RTL source string as a single string.

    Raises:
        ValueError: If the 'original_snippet' defined in the patch is not found 
            exactly as-is within the source code.
    """
    source = case_files.rtl_source
    original = patch.original_snippet
    replacement = patch.patched_snippet

    # 1. Try exact match first
    if original in source:
        return source.replace(original, replacement, 1)

    # 2. Try line-by-line fuzzy match (ignores leading whitespace differences)
    norm_source = _normalize(source)
    norm_original = _normalize(original)

    if norm_original in norm_source:
        # Find the actual block in the original source using regex
        pattern = r"[ \t]*" + r"[ \t\n]*".join(
            re.escape(line.strip()) for line in original.strip().splitlines() if line.strip()
        )
        match = re.search(pattern, source)
        if match:
            return source[:match.start()] + replacement + source[match.end():]

    # 3. Fallback: raise with diagnostic info
    raise ValueError(
        f"Original snippet not found in '{case_files.rtl_filename}'.\n"
        f"Snippet tried:\n{repr(original)}\n\n"
        f"Source (first 500 chars):\n{repr(source[:500])}"
    )
