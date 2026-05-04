# Architecture

## Overview

This project is a **Temporal-powered agentic RTL debugger** that orchestrates a full debug cycle — from loading hardware case files to applying an LLM-generated patch and rerunning verification — as a durable, resumable workflow.

The design goal is to demonstrate how agentic AI workflows can be integrated into chip verification processes in a controlled, auditable way, with a mandatory human approval gate before any patch is applied to the RTL source.

## Design principles

The project follows a strict separation between:

- **Workflow code** (`app/workflows.py`): purely deterministic orchestration. No I/O, no subprocess calls, no LLM calls. Only sequences activity calls, manages state, handles signals and queries.
- **Activity code** (`app/activities.py`): all side effects live here — filesystem access, subprocess execution (`iverilog`, `vvp`), LLM API calls, log writes.

This separation is mandatory because Temporal replays workflow history to resume execution safely after crashes or worker restarts. Any non-deterministic operation inside the workflow would break replay.

## Runtime entry points

| Script | Command | Purpose |
|---|---|---|
| `run_worker.py` | `python run_worker.py` | Start the Temporal Worker, register workflow and activities |
| `run_starter.py` | `python run_starter.py counter_bug` | Launch a new workflow execution for a given `case_id` |
| `run_signal.py` | `python run_signal.py rtl-debug-counter_bug approve` | Send the human approval signal to a running execution |

## Workflow structure

The main orchestration logic lives in `app/workflows.py` as `RTLDebugWorkflow`.

### State managed by the workflow

- `_status`: current phase label, readable via the `get_status` Query
- `_approval_decision`: set when the `submit_approval` Signal is received
- `_report`: the aggregated `DebugReport`, readable via the `get_report` Query

### Signal and Query handlers

- **Signal `submit_approval`**: receives the human approval decision (`approved` / `rejected`) and unblocks `workflow.wait_condition()`.
- **Query `get_status`**: returns the current phase label without mutating state.
- **Query `get_report`**: returns the full `DebugReport` once available.

The human-in-the-loop gate is implemented with `workflow.wait_condition(lambda: self._approval_decision is not None, timeout=timedelta(hours=24))`, which lets the execution pause durably for up to 24 hours without consuming any compute resources.

## Activity pipeline

All ten activities are implemented and verified end-to-end on the `counter_bug` case.

| Phase | Activity | Input → Output |
|---|---|---|
| 3 | `load_case_files` | `case_id` → `CaseFiles` |
| 3 | `run_compile` | `CaseFiles` → `SimulationResult` (compile log saved to `outputs/logs/`) |
| 3 | `run_simulation` | `CaseFiles` → `SimulationResult` (simulation log saved to `outputs/logs/`) |
| 4 | `parse_simulation_log` | `SimulationResult` → `FailureSummary` |
| 4 | `build_context` | `(CaseFiles, FailureSummary)` → `str` (focused RTL window) |
| 5 | `generate_root_cause` | `(CaseFiles, FailureSummary, str)` → `RootCauseAnalysis` |
| 5 | `generate_patch` | `(CaseFiles, RootCauseAnalysis)` → `PatchProposal` |
| 7 | `apply_patch` | `(CaseFiles, PatchProposal)` → patched file written to `outputs/patched/` |
| 7 | `rerun_simulation` | `CaseFiles` → `SimulationResult` (patched rerun, logs to `outputs/logs/`) |
| 7 | `save_report` | `DebugReport` → JSON + Markdown saved to `outputs/reports/` |

## LLM integration

LLM calls are isolated in `app/llm_client.py` via the `LLMClient` class. Provider and model are configured via environment variables (`LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`).

Prompts are defined in `app/prompts.py`:

- `root_cause_prompt()`: instructs the model to produce a structured JSON `RootCauseAnalysis` given the RTL context and failure summary.
- `patch_proposal_prompt()`: instructs the model to produce a minimal `PatchProposal` JSON given the root cause analysis.

Both activities use `LLMClient._parse_json()` to extract JSON from model output that may include markdown fences or leading prose. Malformed output raises `ValueError`, which Temporal treats as a retryable error (max 3 attempts, exponential backoff).

## Data model

All typed objects exchanged between activities are defined in `app/models.py` using Pydantic v2.

| Model | Description |
|---|---|
| `CaseFiles` | Full input bundle for a debug case (RTL source, testbench, spec) |
| `SimulationResult` | Output of compile or simulate steps, including pass/fail and log text |
| `FailureSummary` | Structured extraction of the primary simulation failure |
| `RootCauseAnalysis` | LLM-structured diagnosis with confidence score and suspected lines |
| `PatchProposal` | Minimal code patch (old_code / new_code strings) with explanation |
| `ApprovalSignal` | Human decision payload carried by the `submit_approval` Signal |
| `DebugReport` | Aggregated final report with `to_markdown()` for human-readable output |

## Supporting modules

| Module | Purpose |
|---|---|
| `app/config.py` | Environment-based runtime configuration via `python-dotenv` |
| `app/log_parser.py` | Regex-based extraction of primary failure from `vvp` output |
| `app/context_builder.py` | RTL context window (±8 lines around suspected lines) |
| `app/patcher.py` | Safe `str.replace` patch application with validation |
| `app/llm_client.py` | Async LLM wrapper with JSON extraction and retry logic |
| `app/prompts.py` | Prompt templates for root cause and patch activities |
| `tools/simulation.py` | Async subprocess wrapper for `iverilog` and `vvp` |
| `tools/file_reader.py` | Case file loader from `cases/<case_id>/` |
| `tools/diff_utils.py` | Unified diff generation with `difflib` |

## Output structure

All runtime artefacts are written under `outputs/` and excluded from version control:

```
outputs/
├── logs/
│   ├── <case_id>_compile.log
│   ├── <case_id>_simulation.log
│   ├── <case_id>_patch_compile.log
│   └── <case_id>_patch_simulation.log
├── patched/
│   └── <case_id>/<rtl_filename>
└── reports/
    ├── <case_id>_report.json
    └── <case_id>_report.md
```

## Human-in-the-loop model

An LLM-generated patch is never applied automatically. The workflow pauses after `generate_patch` and waits for a `submit_approval` Signal carrying `{"decision": "approved"}` or `{"decision": "rejected"}`. Only on approval does execution continue to `apply_patch` and `rerun_simulation`.

This design frames the system as a **controlled verification assistant**: the LLM proposes, the engineer decides.

## Current status

All phases from 1 to 7 are implemented and verified end-to-end on the `counter_bug` case. The full workflow executes to `WorkflowExecutionCompleted` with `simulation_passed: true` after patch application.

Known improvement area: the patch prompt can be tightened to enforce a correct `if/else` block structure inside `always @(posedge clk)` instead of relying on the model to produce syntactically idiomatic Verilog.
