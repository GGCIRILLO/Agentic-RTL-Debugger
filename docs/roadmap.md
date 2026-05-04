# Roadmap

## Current state

The repository already includes the base project structure together with a working Temporal skeleton for the main workflow, worker startup, workflow starter, and approval signaling.

The current milestone achieved is: **Phase 2 — minimal Temporal workflow skeleton**.

## Phase 1 — Environment and project setup

### Status
Partially completed.

### Done
- Repository created.
- Base folder structure created.
- `requirements.txt` and `.env.example` added.
- Runtime scripts for worker, starter, and signal added.

### Remaining
- Verify local Temporal server setup end-to-end.
- Verify Python environment and dependency installation on the target machine.
- Install and validate Icarus Verilog locally (`iverilog`, `vvp`). 

## Phase 2 — Minimal Temporal workflow

### Status
Completed as project skeleton.

### Done
- `RTLDebugWorkflow` implemented with `@workflow.defn` and `@workflow.run`.
- Signal handler for approval added.
- Query handlers for workflow inspection added.
- Worker registration implemented in `run_worker.py`.
- Workflow start logic implemented in `run_starter.py`.
- Approval signal sender implemented in `run_signal.py`.

### Remaining
- Run the full skeleton against a live Temporal local instance and validate the event history in Temporal Web UI.

## Phase 3 — First executable hardware case

### Status
Not started.

### Goals
- Create `cases/counter_bug/`.
- Implement `load_case_files`.
- Implement `run_compile`.
- Implement `run_simulation`.
- Save compile and simulation logs to `outputs/logs/`. 

### Deliverable
A reproducible failing Verilog test case that can be launched through the Temporal workflow.

## Phase 4 — Failure parsing and context extraction

### Status
Not started.

### Goals
- Implement `parse_simulation_log` using the existing parser utilities.
- Implement `build_context` using the existing context builder.
- Produce structured `FailureSummary` objects from real simulation output.

### Deliverable
The workflow can move from raw failure logs to structured, minimal diagnostic context.

## Phase 5 — LLM integration

### Status
Not started.

### Goals
- Implement `llm_client.py` wiring in activities.
- Implement `generate_root_cause`.
- Implement `generate_patch`.   
- Keep outputs structured and Pydantic-validated.

### Notes
The choice between remote APIs and a local model is intentionally deferred to a later stage because it is not needed to validate the Temporal workflow shape first.

## Phase 6 — Human approval loop

### Status
Partially prepared.

### Done
- Signal plumbing already exists in workflow and CLI signal sender.

### Remaining
- Validate the end-to-end pause/resume flow on a real patch proposal.
- Optionally add query commands for easier live demo inspection.

## Phase 7 — Patch application and rerun

### Status
Not started.

### Goals
- Implement `apply_patch`.
- Implement `rerun_simulation`.
- Implement `save_report`.
- Save JSON and Markdown reports under `outputs/reports/`. [file:1]

### Deliverable
A complete before/after debug run with approval status and rerun outcome.

## Phase 8 — Demo polish

### Status
Not started.

### Goals
- Add at least one extra bug case beyond `counter_bug`.
- Improve README.
- Add architecture notes and demo instructions.
- Prepare a short 2–3 minute live walkthrough.

## Suggested immediate next step

The highest-value next implementation step is **Phase 3**, because it turns the current skeleton into a workflow that can execute real hardware toolchain steps and produce real artifacts.