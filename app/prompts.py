"""Prompt templates for root cause analysis and patch proposal.

Each function returns a list of messages in OpenAI chat format.
Anthropic messages are structurally identical (role / content).
"""

from __future__ import annotations

from app.models import CaseFiles, FailureSummary, RootCauseAnalysis


def root_cause_prompt(
    case_files: CaseFiles,
    failure: FailureSummary,
    context: str,
) -> list[dict]:
    system = (
        "You are an expert RTL verification engineer. "
        "Analyse the provided Verilog simulation failure and return a structured JSON "
        "diagnosis with keys: summary, suspected_module, suspected_lines (list of ints), "
        "confidence (0.0-1.0), explanation."
    )
    user = f"""## Specification\n{case_files.spec}\n
## RTL Source ({case_files.rtl_filename})\n```verilog\n{case_files.rtl_source}\n```\n
## Testbench ({case_files.tb_filename})\n```verilog\n{case_files.testbench}\n```\n
## Simulation Failure\n{failure.raw_failure}\n
## Relevant Context\n{context}\n
Respond ONLY with valid JSON matching the schema above."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def patch_proposal_prompt(
    case_files: CaseFiles,
    root_cause: RootCauseAnalysis,
) -> list[dict]:
    system = (
        "You are an expert RTL verification engineer. "
        "Given the root cause analysis, produce the MINIMAL patch. "
        "Return JSON with keys: original_snippet, patched_snippet, explanation, diff."
    )
    user = f"""## RTL Source ({case_files.rtl_filename})\n```verilog\n{case_files.rtl_source}\n```\n
## Root Cause\n{root_cause.summary}\nLines: {root_cause.suspected_lines}\n{root_cause.explanation}\n
Respond ONLY with valid JSON matching the schema above."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
