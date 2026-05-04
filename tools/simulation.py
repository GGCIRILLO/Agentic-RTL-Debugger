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

    Args:
        rtl_path: Path to the Verilog RTL source file.
        tb_path: Path to the Verilog testbench file.
        output_path: Path where the compiled simulation binary should be saved.

    Returns:
        A tuple of (success_boolean, combined_stdout_stderr_log).
    """
    output_path = Path(output_path)
    # Run in the directory of the output binary to keep things contained
    cwd = str(output_path.parent)
    cmd = ["iverilog", "-g2012", "-o", output_path.name, str(rtl_path), str(tb_path)]
    
    logger.debug("Compile command: %s (cwd: %s)", " ".join(cmd), cwd)
    rc, stdout, stderr = await _run_command(cmd, cwd=cwd)
    log = (stdout + stderr).strip()
    return rc == 0, log


async def run_vvp(binary_path: str | Path) -> tuple[bool, str]:
    """Run a compiled Verilog binary with vvp.

    Args:
        binary_path: Path to the compiled simulation binary.

    Returns:
        A tuple of (simulation_passed_boolean, simulation_log).
        Simulation is considered passing when no FAILED / ERROR keyword is found
        and the process exits with code 0.
    """
    binary_path = Path(binary_path)
    # Run in the same directory as the binary so VCD files etc. are generated there
    cwd = str(binary_path.parent)
    cmd = ["vvp", binary_path.name]
    
    logger.debug("Simulation command: %s (cwd: %s)", " ".join(cmd), cwd)
    rc, stdout, stderr = await _run_command(cmd, cwd=cwd)
    log = (stdout + stderr).strip()

    failed_keywords = ["FAILED", "ERROR", "MISMATCH", "ASSERTION"]
    simulation_passed = rc == 0 and not any(
        kw in log.upper() for kw in failed_keywords
    )
    return simulation_passed, log
