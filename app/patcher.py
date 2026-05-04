"""Apply a minimal patch to the RTL source file.

This module will be called by the apply_patch Activity in Phase 7.
"""

from __future__ import annotations

from app.models import CaseFiles, PatchProposal


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

    if original not in source:
        raise ValueError(
            f"Original snippet not found in '{case_files.rtl_filename}'.\n"
            f"Snippet: {original!r}"
        )
    return source.replace(original, patch.patched_snippet, 1)
