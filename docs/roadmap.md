# Roadmap

## Current State

Phases 3 and 4 are fully implemented. The workflow runs end-to-end through simulation, log parsing, and context extraction before hitting the Phase 5 stub boundary at `generate_root_cause`.

**Current milestone: Phase 4 — parsing and context extraction complete.**

## Phase 1 — Environment and Project Setup

**Status: ✅ Complete**

- Repository created
- Base folder structure in place
- `requirements.txt` and `.env.example` added
- Runtime scripts for worker, starter, and signal added
- Local Temporal dev server validated
- Python venv and dependencies installed
- Icarus Verilog (`iverilog`, `vvp`) installed and validated locally

## Phase 2 — Minimal Temporal Workflow Skeleton

**Status: ✅ Complete**

- `RTLDebugWorkflow` implemented with `@workflow.defn` / `@workflow.run`
- Signal handler `submit_approval` implemented with `workflow.wait_condition()`
- Query handlers `get_status` and `get_report` implemented
- Worker registration in `run_worker.py`
- Workflow starter in `run_starter.py`
- Approval signal sender in `run_signal.py`
- Full skeleton run validated against live Temporal local instance
- Event history confirmed clean in Temporal Web UI (SDK: `temporal-python 1.27.0`)

## Phase 3 — First Executable Hardware Case

**Status: ✅ Complete**

- `cases/counter_bug/` created with intentional RTL bug (missing `else` on synchronous reset)
- `load_case_files` implemented — reads spec, RTL, and testbench from `cases/<case_id>/`
- `run_compile` implemented — invokes `iverilog`, persists compile log to `outputs/logs/`
- `run_simulation` implemented — invokes `vvp`, persists simulation log to `outputs/logs/`
- Simulation produces expected 2 failures:
  - `FAILED: expected count=0 after reset, got count=x`
  - `FAILED: expected count=8 after 8 increments, got count=x`
- `SimulationResult` payload confirmed correct in Temporal event history (event_id 19)

## Phase 4 — Failure Parsing and Context Extraction

**Status: ✅ Complete**

- `parse_simulation_log` implemented — delegates to `app.log_parser.parse_log()`
  - Regex patterns cover: `FAILED`, `ERROR`, `ASSERTION FAILED`, `MISMATCH`, `Expected ... got ...`
  - Extracts `file.v:lineno` references into `suspected_lines`
  - Returns typed `FailureSummary` with `raw_failure`, `suspected_module`, `suspected_lines`, `failure_type`
- `build_context` implemented — delegates to `app.context_builder.build_context()`
  - ±8-line window around each suspected line number
  - Falls back to full RTL source when no line numbers available
  - Returns numbered snippet string ready for LLM prompt embedding
- Workflow now advances past parsing to `generate_root_cause` stub (Phase 5 boundary)

## Phase 5 — LLM Integration

**Status: 🔲 Not started**

### Goals

- Implement `generate_root_cause` in `app/activities.py`
  - Use `app/llm_client.py` (OpenAI / Anthropic, configurable via `.env`)
  - Use prompt template from `app/prompts.py`
  - Input: `(CaseFiles, FailureSummary, context_str)`
  - Output: structured `RootCauseAnalysis` (Pydantic, parsed from LLM JSON response)
- Implement `generate_patch`
  - Input: `(CaseFiles, RootCauseAnalysis)`
  - Output: `PatchProposal` with `original_snippet` and `patched_snippet`
- Validate structured JSON output from LLM (use `model_validate_json` or `instructor`)

### Deliverable

Workflow advances to the human-approval pause point with a concrete `PatchProposal` visible in `get_report` query output.

## Phase 6 — Human Approval Loop

**Status: 🟡 Plumbed, not validated end-to-end**

### Done

- Signal plumbing exists in workflow and `run_signal.py`
- `workflow.wait_condition()` with 24-hour timeout in place

### Remaining

- Validate end-to-end pause/resume on a real `PatchProposal` once Phase 5 is done
- Confirm `get_report` query returns the proposal during the wait window
- Test both `approve` and `reject` signal paths

## Phase 7 — Patch Application and Rerun

**Status: 🔲 Not started**

### Goals

- Implement `apply_patch` — write patched RTL to `outputs/patched/<case_id>/`
- Implement `rerun_simulation` — compile and simulate the patched file
- Implement `save_report` — persist `DebugReport` as JSON and Markdown under `outputs/reports/`

### Deliverable

A complete before/after debug run: original failure → LLM patch → human approval → rerun → PASSED (or documented failure if patch is wrong).

## Phase 8 — Demo Polish

**Status: 🔲 Not started**

### Goals

- Add at least one additional bug case beyond `counter_bug`
- Update README with setup instructions and demo walkthrough
- Prepare a 2–3 minute live demo script covering the full workflow lifecycle

## Immediate Next Step

**Phase 5** — implement `generate_root_cause` and `generate_patch` using the LLM client already present in `app/llm_client.py` and the prompt templates in `app/prompts.py`.
