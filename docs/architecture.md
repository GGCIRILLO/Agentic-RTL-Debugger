# Architecture

## Overview

This project is a small **Temporal-powered agentic RTL debugger** built to demonstrate how an AI-assisted verification workflow can be orchestrated as a durable system instead of a fragile script.

The workflow takes a hardware debug case as input, executes simulation-related steps, analyzes failures, proposes a patch, waits for human approval, and then reruns verification. Temporal is the orchestration layer that makes this flow durable, inspectable, and resumable across worker restarts.

## Design principles

The project follows a strict separation between:

- **Workflow code**, which must stay deterministic and only orchestrate state transitions.
- **Activity code**, which contains side effects such as filesystem access, subprocess execution, and future LLM/API calls.

This separation matters because Temporal replays workflow history to resume execution safely after crashes or restarts.

## Runtime entry points

The repository exposes three operational entry points:

- `run_worker.py`: starts the Temporal Worker, connects to the Temporal server, and registers the workflow plus all activities.
- `run_starter.py`: starts a new workflow execution for a selected `case_id`.
- `run_signal.py`: sends an approval or rejection Signal to a running workflow execution.

These three scripts are enough to demonstrate the full orchestration lifecycle: start, pause, inspect, resume.

## Workflow structure

The main orchestration logic lives in `app/workflows.py` inside `RTLDebugWorkflow`.

The workflow currently manages three categories of state:

- current workflow status
- current human approval state
- aggregated debug report

The workflow exposes:

- a **Signal** handler, `submit_approval`, used to inject the human decision into the running execution.
- two **Query** handlers, `get_status` and `get_report`, used to inspect workflow state without mutating it.

The central pause point is implemented with `workflow.wait_condition(...)`, which allows the execution to wait durably for approval instead of blocking in a fragile process-local way.

## Activities

All external operations are modeled as Activities in `app/activities.py`. The current activity list is:

- `load_case_files`
- `run_compile`
- `run_simulation`
- `parse_simulation_log`
- `build_context`
- `generate_root_cause`
- `generate_patch`
- `apply_patch`
- `rerun_simulation`
- `save_report`

At this stage, these Activities are intentionally implemented as stubs raising `NotImplementedError`, because the current milestone focuses on validating the Temporal skeleton first.

## Data model

The shared data model lives in `app/models.py` and uses Pydantic models to keep data passed across steps structured and explicit.

The most important models are:

- `CaseFiles`: input bundle for a debug case
- `SimulationResult`: output of compile/simulate steps
- `FailureSummary`: structured failure extraction
- `RootCauseAnalysis`: structured LLM diagnosis
- `PatchProposal`: minimal code patch proposal
- `ApprovalSignal`: human approval decision
- `DebugReport`: final aggregated report

This makes the workflow easier to reason about and easier to demo, because every step produces a typed artifact instead of ad-hoc dictionaries.

## Supporting modules

Several helper modules are already in place:

- `app/config.py`: environment-based runtime configuration
- `app/log_parser.py`: utilities to extract a primary failure from simulation logs
- `app/context_builder.py`: utilities to build a focused RTL context window
- `app/patcher.py`: patch application logic
- `tools/simulation.py`: subprocess wrapper around `iverilog` and `vvp`
- `tools/file_reader.py`: case file loading helpers
- `tools/diff_utils.py`: unified diff generation

These modules are not fully wired into production activities yet, but they define the intended shape of later implementation phases.

## Human-in-the-loop model

The project is deliberately designed so that an AI-generated patch is never applied automatically without approval. Instead, the workflow pauses after producing a patch proposal and waits for a human Signal, which matches Temporal’s message-passing model for stateful workflows.

This is an important architectural choice because it frames the system as a controlled verification assistant rather than an autonomous code mutator.[file:1]

## Current status

The repository currently contains a working Temporal application skeleton:

- config and runtime entry points are in place
- workflow, signal, and query structure are implemented
- activities are registered in the worker
- helper modules and typed models are present
- execution logic beyond the skeleton remains to be implemented in later phases 