"""Wrapper around Icarus Verilog (iverilog + vvp).

This module contains the subprocess logic used by run_compile and
run_simulation Activities (implemented in Phase 3).
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def _run_command(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run an external command asynchronously; return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(), stderr.decode()


async def compile_verilog(
    rtl_path: str | Path,
    tb_path: str | Path,
    output_path: str | Path,
) -> tuple[bool, str]:
    """Invoke iverilog to compile rtl + testbench into a simulation binary.

    Returns (success, combined_log).
    """
    cmd = ["iverilog", "-o", str(output_path), str(rtl_path), str(tb_path)]
    logger.debug("Compile command: %s", " ".join(cmd))
    rc, stdout, stderr = await _run_command(cmd)
    log = (stdout + stderr).strip()
    return rc == 0, log


async def run_vvp(binary_path: str | Path) -> tuple[bool, str]:
    """Run a compiled Verilog binary with vvp.

    Returns (simulation_passed, log).
    Simulation is considered passing when no FAILED / ERROR keyword is found
    and the process exits with code 0.
    """
    cmd = ["vvp", str(binary_path)]
    logger.debug("Simulation command: %s", " ".join(cmd))
    rc, stdout, stderr = await _run_command(cmd)
    log = (stdout + stderr).strip()

    failed_keywords = ["FAILED", "ERROR", "MISMATCH", "ASSERTION"]
    simulation_passed = rc == 0 and not any(
        kw in log.upper() for kw in failed_keywords
    )
    return simulation_passed, log
