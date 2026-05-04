"""File reading utilities for loading case assets from disk."""

from __future__ import annotations

from pathlib import Path

from app.config import config
from app.models import CaseFiles


def load_case(case_id: str) -> CaseFiles:
    """Read spec, RTL and testbench files from the filesystem for a given case.

    Args:
        case_id: The directory name under the 'cases/' folder.

    Returns:
        A CaseFiles object containing the content of spec.md, the first 
        RTL Verilog file found, and the first testbench (tb_*.v) file found.

    Raises:
        FileNotFoundError: If the case directory, spec.md, RTL file, or 
            testbench file is missing.
    """
    case_dir = Path(config.cases_dir) / case_id
    if not case_dir.is_dir():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    spec_path = case_dir / "spec.md"
    if not spec_path.exists():
        raise FileNotFoundError(f"spec.md not found in {case_dir}")

    verilog_files = sorted(case_dir.glob("*.v"))
    tb_files = [f for f in verilog_files if f.name.startswith("tb_")]
    rtl_files = [f for f in verilog_files if not f.name.startswith("tb_")]

    if not rtl_files:
        raise FileNotFoundError(f"No RTL .v file found in {case_dir}")
    if not tb_files:
        raise FileNotFoundError(f"No testbench tb_*.v file found in {case_dir}")

    rtl_path = rtl_files[0]
    tb_path = tb_files[0]

    return CaseFiles(
        case_id=case_id,
        spec=spec_path.read_text(),
        rtl_source=rtl_path.read_text(),
        testbench=tb_path.read_text(),
        rtl_filename=rtl_path.name,
        tb_filename=tb_path.name,
    )
