"""Prompt templates for root cause analysis and patch proposal.

Each function returns a list of messages in OpenAI chat format.
Anthropic messages are structurally identical (role / content).
"""

from __future__ import annotations

from app.models import CaseFiles, FailureSummary, RootCauseAnalysis, PatchProposal


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


# ---------------------------------------------------------------------------
# Patch proposal
# ---------------------------------------------------------------------------

_PATCH_SYSTEM = """\
You are an expert RTL verification engineer.
Your task is to produce a correct patch for a failing Verilog module.

Patching rules (apply to every case, not just this one):
1. NEVER delete logic without replacing it with the correct behaviour.
   Removing a line is only valid if that line is genuinely dead code with
   no functional role. When in doubt, transform — do not delete.
2. If the root cause is missing conditional branching (e.g. a missing `else`),
   ADD the missing branch. Do not remove the existing branch.
3. If the root cause is a wrong operator, value, or signal name, correct it
   in place. Preserve all surrounding structure.
4. Do not change port declarations, module names, timescale directives,
   parameter lists, or any logic unrelated to the identified bug.
5. The patch must make the testbench PASS according to the spec.
   Correctness takes absolute priority over minimality.
6. Output JSON with exactly these keys:
     original_snippet  – the verbatim lines being replaced (string)
     patched_snippet   – the replacement lines (string)
     explanation       – one concise sentence describing the change
     diff              – unified diff (--- original / +++ patched)

Few-shot example
----------------
Bug: synchronous reset block missing else — counter always increments.

Broken RTL:
    always @(posedge clk) begin
        if (rst)
            count <= 4'b0;
        count <= count + 1;   // executed unconditionally — overwrites reset
    end

Correct patch (add the missing else branch):
    always @(posedge clk) begin
        if (rst)
            count <= 4'b0;
        else
            count <= count + 1;
    end

Diff:
--- original
+++ patched
     if (rst)
         count <= 4'b0;
-    count <= count + 1;
+    else
+        count <= count + 1;

Reason: the second assignment was not redundant — it was simply in the wrong
branch. The fix is to add `else`, not to delete the increment.
"""


def patch_proposal_prompt(
    case_files: CaseFiles,
    root_cause: RootCauseAnalysis,
    sim_result_log: str = "",
    previous_patch: PatchProposal | None = None,
    rerun_log: str = "",
) -> list[dict]:
    """Build the patch-proposal prompt.

    Parameters
    ----------
    case_files:
        Full case bundle (RTL source, testbench, spec).
    root_cause:
        Structured root cause from generate_root_cause.
    sim_result_log:
        Raw simulation log (optional but strongly recommended — pass it
        so the LLM can verify its fix against the actual failure messages).
    """
    user = f"""## Specification
{case_files.spec}

## RTL Source ({case_files.rtl_filename})
```verilog
{case_files.rtl_source}
```

## Testbench ({case_files.tb_filename})
```verilog
{case_files.testbench}
```

## Simulation Failure Log
{sim_result_log or '(not provided)'}

## Root Cause Analysis
Summary: {root_cause.summary}
Suspected lines: {root_cause.suspected_lines}
Explanation: {root_cause.explanation}
"""
    if previous_patch and rerun_log:
        user += f"""
## Previous Attempt Failed
You previously proposed this patch:
```diff
{previous_patch.diff}
```
But it FAILED the verification rerun with this log:
{rerun_log}

CRITICAL INSTRUCTION: Your previous patch was WRONG. You MUST change your approach. 
DO NOT propose the exact same patch again. If you previously tried deleting a block and it failed, you must instead REWRITE or MERGE the logic correctly. 
Please try again and provide a CORRECTED patch.
"""

    user += "\nRemember the patching rules above.\nRespond ONLY with valid JSON matching the schema: original_snippet, patched_snippet, explanation, diff."

    return [
        {"role": "system", "content": _PATCH_SYSTEM},
        {"role": "user", "content": user},
    ]
