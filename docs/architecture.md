# Architecture

## Overview

This project is a small **Temporal-powered agentic RTL debugger** built to demonstrate how an AI-assisted verification workflow can be orchestrated as a durable system instead of a fragile script.

The workflow takes a hardware debug case as input, executes simulation-related steps, analyzes failures, proposes a patch, waits for human approval, and then reruns verification. Temporal is the orchestration layer that makes this flow durable, inspectable, and resumable across worker restarts.

## Design principles

The project follows a strict separation between:

- **Workflow code**, which must stay deterministic and only orchestrate state transitions.
- **Activity code**, which contains side effects such as filesystem access, subprocess execution, and LLM calls.

This separation matters because Temporal replays workflow history to resume execution safely after crashes or restarts.

## Runtime entry points

The repository exposes three operational entry points:

- `run_worker.py`: starts the Temporal Worker, connects to the Temporal server, and registers the workflow plus all activities.
- `run_starter.py`: starts a new workflow execution for a selected `case_id`.
- `run_signal.py`: sends an approval or rejection Signal to a running workflow execution.

These three scripts are enough to demonstrate the full orchestration lifecycle: start, pause, inspect, resume.

## Workflow structure

The main orchestration logic lives in `app/workflows.py` inside `RTLDebugWorkflow`.

The workflow manages three categories of state:

- current workflow status
- current human approval state
- aggregated debug report

The workflow exposes:

- a **Signal** handler, `submit_approval`, used to inject the human decision into the running execution.
- two **Query** handlers, `get_status` and `get_report`, used to inspect workflow state without mutating it.

The central pause point is implemented with `workflow.wait_condition(...)`, which allows the execution to wait durably for approval instead of blocking in a fragile, process-local way.

## Activities

All external operations are modeled as Activities in `app/activities.py`. The current implementation status per phase is:

| Activity | Phase | Status |
|---|---|---|
| `load_case_files` | 3 | Implemented |
| `run_compile` | 3 | Implemented |
| `run_simulation` | 3 | Implemented |
| `parse_simulation_log` | 4 | Stub |
| `build_context` | 4 | Stub |
| `generate_root_cause` | 5 | Stub |
| `generate_patch` | 5 | Stub |
| `apply_patch` | 7 | Stub |
| `rerun_simulation` | 7 | Stub |
| `save_report` | 7 | Stub |

## Data model

The shared data model lives in `app/models.py` and uses Pydantic models to keep data passed across steps structured and explicit.

The most important models are:

- `CaseFiles`: input bundle for a debug case (spec, RTL source, testbench)
- `SimulationResult`: output of compile and simulate steps
- `FailureSummary`: structured failure extraction from simulation logs
- `RootCauseAnalysis`: structured LLM diagnosis with confidence score
- `PatchProposal`: minimal code patch proposed by the LLM
- `ApprovalSignal`: human approval or rejection decision
- `DebugReport`: final aggregated report with before/after outcome

This makes the workflow easier to reason about and easier to demo because every step produces a typed artifact instead of ad-hoc dictionaries.

## Supporting modules

| Module | Purpose |
|---|---|
| `app/config.py` | Environment-based runtime configuration |
| `app/log_parser.py` | Extract primary failure from simulation logs |
| `app/context_builder.py` | Build a focused RTL context window around suspected lines |
| `app/patcher.py` | Apply a minimal snippet replacement to the RTL source |
| `app/prompts.py` | Prompt templates for root cause and patch LLM calls |
| `app/llm_client.py` | Async LLM client facade (OpenAI / Anthropic / local) |
| `tools/simulation.py` | Async subprocess wrapper for `iverilog` and `vvp` |
| `tools/file_reader.py` | Load case files from `cases/<case_id>/` |
| `tools/diff_utils.py` | Unified diff generation for before/after comparison |

## Hardware cases

Each debug case lives in `cases/<case_id>/` and contains four files:

| File | Purpose |
|---|---|
| `spec.md` | Textual specification of the correct behaviour |
| `<module>.v` | Verilog RTL source with an intentional bug |
| `tb_<module>.v` | Testbench that exposes the bug and prints FAILED/PASSED |
| `expected.md` | Known root cause and minimal correct fix (ground truth) |

Current cases:

- `counter_bug`: 4-bit synchronous counter with a wrong reset condition ordering.

## Simulation flow (Phase 3)

When Phase 3 activities execute, the simulation flow works as follows:

1. `load_case_files` reads `spec.md`, `<module>.v`, and `tb_<module>.v` from disk.
2. `run_compile` invokes `iverilog -o sim.out <tb>.v <rtl>.v` and saves the compile log to `outputs/logs/<case_id>_compile.log`.
3. `run_simulation` invokes `vvp sim.out` and saves the simulation log to `outputs/logs/<case_id>_simulation.log`.

The compiled binary is written to a stable path under the OS temp directory (`/tmp/rtl_debugger/<case_id>/sim.out`) so both activities share it without passing binary data through Temporal.

## Human-in-the-loop model

The project is deliberately designed so that an AI-generated patch is never applied automatically without approval. Instead, the workflow pauses after producing a patch proposal and waits for a human Signal, which matches Temporal's message-passing model for stateful workflows.

This is an important architectural choice because it frames the system as a controlled verification assistant rather than an autonomous code mutator.

## Current status

- Phase 1: complete.
- Phase 2: complete — Temporal skeleton running and validated.
- Phase 3: complete — `counter_bug` case files in place, three activities implemented and wired.
- Phases 4–7: stubs, to be implemented in subsequent phases.
