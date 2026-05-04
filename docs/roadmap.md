# Roadmap

## Current state

Phases 1 through 7 are fully implemented and verified end-to-end on the `counter_bug` case. The Temporal workflow executes all 10 activities, pauses for human approval, applies the LLM-generated patch, reruns simulation, and saves the final report. The workflow completes with `WorkflowExecutionCompleted` and `simulation_passed: true`.

---

## Phase 1 — Environment and project setup

### Status: ✅ Completed

- Repository created with base folder structure.
- `requirements.txt` and `.env.example` added.
- Runtime entry points (`run_worker.py`, `run_starter.py`, `run_signal.py`) added.
- Python environment and dependencies verified locally.
- Icarus Verilog (`iverilog`, `vvp`) validated on the target machine.

---

## Phase 2 — Minimal Temporal workflow skeleton

### Status: ✅ Completed

- `RTLDebugWorkflow` implemented with `@workflow.defn` / `@workflow.run`.
- Signal handler `submit_approval` with `workflow.wait_condition()` (24 h timeout).
- Query handlers `get_status` and `get_report`.
- Worker registration, workflow starter, and signal sender scripts all working.

---

## Phase 3 — First executable hardware case

### Status: ✅ Completed

- `cases/counter_bug/` created with intentional RTL bug (missing `else` in `always` block).
- `load_case_files` implemented — loads RTL, testbench, and spec from `cases/<case_id>/`.
- `run_compile` implemented — invokes `iverilog`, saves compile log to `outputs/logs/`.
- `run_simulation` implemented — invokes `vvp`, saves simulation log to `outputs/logs/`.
- Verified: simulation correctly reports 2 failures on the buggy RTL.

---

## Phase 4 — Failure parsing and context extraction

### Status: ✅ Completed

- `parse_simulation_log` implemented — extracts `FailureSummary` from `vvp` output using regex.
- `build_context` implemented — produces a focused RTL context window (±8 lines around suspected lines).
- Verified: `FailureSummary` correctly identifies `failure_type` and `suspected_lines`.

---

## Phase 5 — LLM integration

### Status: ✅ Completed

- `app/llm_client.py` implemented — async `LLMClient` with provider switching (`openai` / `anthropic`), JSON extraction from markdown-fenced or prose-wrapped model output, and error handling.
- `app/prompts.py` implemented — `root_cause_prompt()` and `patch_proposal_prompt()` templates.
- `generate_root_cause` implemented — calls LLM, validates response into `RootCauseAnalysis` (confidence, suspected lines, summary).
- `generate_patch` implemented — calls LLM, validates response into `PatchProposal` (old_code, new_code, explanation).
- Verified: LLM correctly identified the missing `else` branch with `confidence: 0.9` and produced a working patch.

### Known improvement

The patch prompt should be tightened to explicitly require a correct `if/else` block inside the `always @(posedge clk)` body, to avoid structurally malformed but functionally accepted Verilog.

---

## Phase 6 — Human approval loop

### Status: ✅ Completed (validated end-to-end)

- Signal plumbing already present from Phase 2.
- Validated: workflow pauses at `TimerStarted` (event 47), receives `submit_approval` signal (event 48), cancels timer (event 52), and continues to `apply_patch`.
- `run_signal.py approve` tested successfully in the `counter_bug` run.

---

## Phase 7 — Patch application and rerun

### Status: ✅ Completed

- `apply_patch` implemented — applies `PatchProposal` to RTL source, writes patched file to `outputs/patched/<case_id>/`.
- `rerun_simulation` implemented — recompiles from the patched RTL (original testbench), saves rerun logs to `outputs/logs/`.
- `save_report` implemented — writes `DebugReport` as both JSON and Markdown to `outputs/reports/`.
- Verified: rerun simulation returns `simulation_passed: true` and `"PASSED: all checks passed"` for `counter_bug`.

---

## Phase 8 — Demo polish

### Status: 🔲 Not started

### Goals

- Add a second bug case (e.g. `fsm_bug`) to demonstrate generalisability.
- Improve the patch prompt to enforce syntactically correct `if/else` Verilog structure.
- Fix `.gitignore` to exclude all Verilog artefacts (`*.v` generated files, `*.out`, `*.vvp`, `*.vcd`) and clean up any spurious root-level files.
- Update `README.md` with full setup instructions and a demo walkthrough.
- Prepare a 2–3 minute live demo script.

### Suggested immediate next step

The highest-value next step is adding `fsm_bug` as a second case, which validates that the workflow is not hardcoded to the counter case and makes the demo more compelling.
