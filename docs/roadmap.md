# Roadmap

## Current state

The current milestone achieved is: **Phase 3 — first executable hardware case**.

Phases 1, 2 and 3 are complete. The workflow can now load a real Verilog case, compile it with Icarus Verilog, run the simulation, and save the logs to disk. The next step is to parse the failure output and extract structured context for the LLM.

## Phase 1 — Environment and project setup

### Status
Complete.

### Done
- Repository created.
- Base folder structure created.
- `requirements.txt` and `.env.example` added.
- Runtime scripts for worker, starter, and signal added.
- Icarus Verilog installed and validated locally (`iverilog`, `vvp`).
- Temporal local dev server validated end-to-end.

## Phase 2 — Minimal Temporal workflow

### Status
Complete.

### Done
- `RTLDebugWorkflow` implemented with `@workflow.defn` and `@workflow.run`.
- Signal handler for patch approval added.
- Query handlers for workflow inspection added.
- Worker registration implemented in `run_worker.py`.
- Workflow start logic implemented in `run_starter.py`.
- Approval signal sender implemented in `run_signal.py`.
- Skeleton validated against live Temporal dev server.

## Phase 3 — First executable hardware case

### Status
Complete.

### Done
- `cases/counter_bug/` created with `spec.md`, `counter.v`, `tb_counter.v`, `expected.md`.
- `load_case_files` implemented: reads spec, RTL, and testbench from disk.
- `run_compile` implemented: invokes `iverilog`, saves compile log to `outputs/logs/`.
- `run_simulation` implemented: invokes `vvp`, saves simulation log to `outputs/logs/`.
- Bug is reproducible: testbench prints `FAILED` on every run against `counter.v`.

## Phase 4 — Failure parsing and context extraction

### Status
Not started.

### Goals
- Implement `parse_simulation_log` using the existing parser utilities in `app/log_parser.py`.
- Implement `build_context` using the existing context builder in `app/context_builder.py`.
- Produce structured `FailureSummary` objects from real simulation output.

### Deliverable
The workflow advances from raw failure logs to structured, minimal diagnostic context ready for the LLM.

## Phase 5 — LLM integration

### Status
Not started.

### Goals
- Wire `app/llm_client.py` into the activities.
- Implement `generate_root_cause`.
- Implement `generate_patch`.
- Keep all LLM outputs Pydantic-validated.

### Notes
The choice between remote APIs and a local model (e.g. Ollama) is intentionally deferred. The Temporal workflow shape is independent of the LLM backend.

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
- Save JSON and Markdown reports under `outputs/reports/`.

### Deliverable
A complete before/after debug run: original failure, LLM diagnosis, proposed patch, human approval, rerun outcome.

## Phase 8 — Demo polish

### Status
Not started.

### Goals
- Add at least one extra bug case beyond `counter_bug`.
- Update README with full setup and demo instructions.
- Prepare a short 2–3 minute live walkthrough script.

## Suggested immediate next step

Phase 4: implement `parse_simulation_log` and `build_context` so the workflow can produce a structured `FailureSummary` from the real simulation logs already saved to disk.
