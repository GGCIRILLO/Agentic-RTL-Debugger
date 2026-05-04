# Architecture

## Overview

This project is a **Temporal-powered agentic RTL debugger** built to demonstrate how an AI-assisted verification workflow can be orchestrated as a durable, inspectable system instead of a fragile script.

The workflow takes a hardware debug case as input, executes simulation-related steps, analyzes failures, proposes a patch, waits for human approval, and then reruns verification. Temporal is the orchestration layer that makes this flow durable and resumable across worker restarts.

## Design Principles

The project enforces a strict separation between:

- **Workflow code** — must stay fully deterministic. It only orchestrates state transitions and schedules activities. No I/O, no subprocesses, no randomness.
- **Activity code** — contains all side effects: filesystem access, subprocess execution (iverilog, vvp), LLM/API calls. Each activity is independently retried by Temporal on failure.

This separation is not optional: Temporal replays the workflow event history to resume execution after crashes or worker restarts. Any non-determinism in the workflow function would cause a non-determinism error on replay.

## Runtime Entry Points

| Script | Command | Purpose |
|---|---|---|
| `run_worker.py` | `python run_worker.py` | Start the Temporal Worker, register workflow and activities |
| `run_starter.py` | `python run_starter.py counter_bug` | Start a new workflow execution for a case |
| `run_signal.py` | `python run_signal.py rtl-debug-counter_bug approve` | Send human approval/rejection signal |

## Workflow Structure

The main orchestration logic lives in `app/workflows.py` inside `RTLDebugWorkflow`.

The workflow manages three categories of state:
- current execution status (string label)
- human approval state (enum: pending / approved / rejected)
- aggregated `DebugReport` built incrementally across steps

The workflow exposes:
- a **Signal** handler `submit_approval` — injects the human decision into the running execution via Temporal message passing
- two **Query** handlers `get_status` and `get_report` — read workflow state without mutating it, inspectable from the Temporal Web UI at any point

The central pause point uses `workflow.wait_condition(lambda: self._approval is not None, timeout=timedelta(hours=24))`, which durably parks the execution until a signal arrives or the timeout expires.

## Activity Pipeline

Activities execute in order inside the workflow. Each produces a typed Pydantic artifact consumed by the next step.

| # | Activity | Phase | Status | Input → Output |
|---|---|---|---|---|
| 1 | `load_case_files` | 3 | ✅ Done | `case_id: str` → `CaseFiles` |
| 2 | `run_compile` | 3 | ✅ Done | `CaseFiles` → `SimulationResult` |
| 3 | `run_simulation` | 3 | ✅ Done | `CaseFiles` → `SimulationResult` |
| 4 | `parse_simulation_log` | 4 | ✅ Done | `SimulationResult` → `FailureSummary` |
| 5 | `build_context` | 4 | ✅ Done | `(CaseFiles, FailureSummary)` → `str` |
| 6 | `generate_root_cause` | 5 | 🔲 Stub | `(CaseFiles, FailureSummary, str)` → `RootCauseAnalysis` |
| 7 | `generate_patch` | 5 | 🔲 Stub | `(CaseFiles, RootCauseAnalysis)` → `PatchProposal` |
| — | *(human approval signal)* | 6 | ✅ Plumbed | `ApprovalSignal` via Temporal Signal |
| 8 | `apply_patch` | 7 | 🔲 Stub | `(CaseFiles, PatchProposal)` → `None` |
| 9 | `rerun_simulation` | 7 | 🔲 Stub | `CaseFiles` → `SimulationResult` |
| 10 | `save_report` | 7 | 🔲 Stub | `DebugReport` → `None` |

## Phase 4 — Parsing & Context Detail

### `parse_simulation_log`

Delegates to `app.log_parser.parse_log(sim_result.simulation_log)`. The parser applies a set of regex patterns covering common vvp failure formats:

- `FAILED: ...` — testbench assertion failures (primary pattern for demo cases)
- `ERROR: ...` — tool-level errors
- `ASSERTION FAILED: ...` — SystemVerilog assertions
- `MISMATCH: ...` and `Expected ..., got ...` — comparison-style failures

It also extracts `file.v:lineno` references from any line in the log to populate `suspected_lines`. Returns a `FailureSummary` with `raw_failure`, `suspected_module`, `suspected_lines`, and `failure_type`.

**Example output for `counter_bug`:**
```
raw_failure    : "FAILED: expected count=0 after reset, got count=x\nFAILED: expected count=8 after 8 increments, got count=x\nFAILED: 2 error(s) found"
suspected_module: "cases/counter_bug/tb_counter.v"
suspected_lines : [73]
failure_type   : "simulation_failure"
```

### `build_context`

Delegates to `app.context_builder.build_context(case_files, failure)`. Uses a ±8-line window around each suspected line number. When no line numbers are available it falls back to the full RTL source.

Returns a numbered snippet string:
```
  1  // 4-bit synchronous counter
  ...
  11     always @(posedge clk) begin
  12         if (rst)
  13             count <= 4'b0;
  14         count <= count + 1;
  15     end
```

This snippet is passed verbatim to the LLM prompt in Phase 5.

## Data Model

All inter-activity data is defined in `app/models.py` as frozen Pydantic v2 models.

| Model | Produced by | Consumed by |
|---|---|---|
| `CaseFiles` | `load_case_files` | `run_compile`, `run_simulation`, `build_context`, `generate_root_cause`, `generate_patch`, `apply_patch` |
| `SimulationResult` | `run_compile`, `run_simulation`, `rerun_simulation` | `parse_simulation_log` |
| `FailureSummary` | `parse_simulation_log` | `build_context`, `generate_root_cause` |
| `RootCauseAnalysis` | `generate_root_cause` | `generate_patch`, `DebugReport` |
| `PatchProposal` | `generate_patch` | `apply_patch`, `DebugReport` |
| `ApprovalSignal` | human via `run_signal.py` | workflow signal handler |
| `DebugReport` | assembled by workflow | `save_report` |

## Supporting Modules

| Module | Role |
|---|---|
| `app/config.py` | Environment-based runtime configuration via `python-dotenv` |
| `app/log_parser.py` | Regex-based failure extraction from vvp logs |
| `app/context_builder.py` | ±8-line RTL window builder around suspected lines |
| `app/patcher.py` | Safe `str.replace` patch application |
| `app/prompts.py` | LLM prompt templates (used in Phase 5) |
| `app/llm_client.py` | Async LLM client wrapper (OpenAI / Anthropic) |
| `tools/simulation.py` | Async subprocess wrappers for `iverilog` and `vvp` |
| `tools/file_reader.py` | Case directory loader and validator |
| `tools/diff_utils.py` | Unified diff generation with `difflib` |

## Human-in-the-Loop Model

An AI-generated patch is never applied automatically. The workflow pauses after `generate_patch` and waits for a human Signal carrying an `ApprovalSignal` (approved / rejected). This is a deliberate architectural choice: the system is a controlled verification assistant, not an autonomous code mutator.

The 24-hour timeout on `wait_condition` ensures the workflow eventually fails cleanly if no human responds, leaving a complete audit trail in Temporal event history.

## Observed Event History (Phase 3 + 4 boundary)

The first fully correct run reached event_id 25 before failing at `parse_simulation_log` (stub). With Phase 4 implemented, the next run will advance to `generate_root_cause` (next stub boundary). The expected clean event sequence is:

```
1   WorkflowExecutionStarted
2-4  WorkflowTask (initial)
5-7  load_case_files      → CaseFiles
8-10 WorkflowTask
11-13 run_compile         → SimulationResult (compiled=true)
14-16 WorkflowTask
17-19 run_simulation      → SimulationResult (simulation_passed=false, 2 FAILED lines)
20-22 WorkflowTask
23-25 parse_simulation_log → FailureSummary
26-28 WorkflowTask
29-31 build_context       → str (RTL snippet)
32-34 WorkflowTask
35-37 generate_root_cause → NotImplementedError (Phase 5 boundary)
```
