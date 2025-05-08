# AI Agent Development Workflow

This document outlines the automated development workflow implemented in the `ethereum_project`. This system leverages a Large Language Model (LLM) agent, orchestrated by scripts and guided by prompt files, to continuously enhance the codebase, manage tasks, and maintain quality standards.

## Ⅰ. Overview and Goal

The primary goal of this workflow is to automate significant portions of the software development lifecycle for the `ethereum_project`. This includes task management, code implementation, testing, quality assurance, and logging, with the aim of improving development velocity and consistency while minimizing direct human intervention for routine tasks. The system is designed to operate autonomously, driven by a predefined roadmap and a set of operational prompts.

This workflow is currently active and drives the evolution of the project. Human developers should be aware of its operation, especially when reviewing agent-generated code or modifying core scripts and prompts that govern the agent's behavior.

## Ⅱ. Core Components

The autonomous workflow relies on several key files and directories:

*   **`prompts/starter_prompt.txt`**:
    *   **Role**: The main entry point or "brain" for the LLM agent. It defines the overall operational phases, a machine-readable checklist for the agent's workflow, and the currently active development ticket.
    *   **Management**: This file is dynamically updated by `scripts/roadmap_sync.py` (or a similar script) during the "Roadmap Sync" phase to reflect the current task.

*   **`prompts/roadmap.jsonl`**:
    *   **Role**: The authoritative source for all development tasks, organized as a JSON Lines file where each line is a JSON object representing a task, section, milestone, or gate.
    *   **Content**: Each task object includes an `ID`, `Task_Title`, `Status` (e.g., "DONE", "IN PROGRESS", "NOT STARTED"), dependencies, and other relevant metadata.
    *   **Management**: Task statuses are updated by the agent workflow (likely via `scripts/roadmap_sync.py` or `rollover_prompt.txt` logic) as tasks are completed and new ones begin.

*   **`scripts/qa_audit.py`**:
    *   **Role**: Performs automated quality assurance checks on the codebase.
    *   **Functionality**: Can run in "delta" mode (checking only changed files since the last audit) or "full" mode. It executes linters (Ruff), type checkers (MyPy), complexity analysis (Radon), and tests (Pytest with coverage).
    *   **Output**: Generates scores for various quality axes and updates `prompts/quality_scoreboard.md` and `quality_scoreboard.json`.

*   **`scripts/roadmap_sync.py`** (or equivalent logic implied by `starter_prompt.txt` and `rollover_prompt.txt`):
    *   **Role**: Manages the state of the roadmap and the agent's current focus.
    *   **Functionality**: Determines the active ticket based on `prompts/roadmap.jsonl`. Performs "rollover" operations: marks the previously completed ticket as "DONE" and the next ticket as "IN PROGRESS" in `roadmap.jsonl`. It also updates `prompts/starter_prompt.txt` (specifically §❸ Current ticket) to reflect the new active task.

*   **Prompt Files for Specific Agent Tasks**:
    *   **`prompts/codebase_review_prompt.txt`**: Guides the agent in performing comprehensive static reviews of the repository, focusing on documentation, code quality, security, testing, and DevOps aspects. It defines scoring criteria and reporting guidelines.
    *   **`prompts/roadmap_status_evaluation_prompt.txt`**: Instructs the agent on how to parse `prompts/roadmap.jsonl` to determine the currently active roadmap step and check for synchronization issues between the roadmap and the codebase.
    *   **`prompts/rollover_prompt.txt`**: Defines the process for the agent to update `starter_prompt.txt` and `roadmap.jsonl` when transitioning between tickets, incorporating lessons learned.

*   **Output & State Files**:
    *   **`prompts/quality_scoreboard.md`**: A human-readable history of quality audit scores.
    *   **`quality_scoreboard.json`** (root): A machine-readable summary of the latest quality audit scores. (Currently, this file is empty, indicating the QA process might be initializing or results are primarily in the Markdown version).
    *   **`prompts/development_log.md`**: A human-readable log of development activities.
    *   **`development_log.jsonl`** (expected): A structured, machine-readable log of development activities (implied by `starter_prompt.txt`).
    *   **`.qa_audit_cache`**: Stores the SHA of the last commit audited to enable delta assessments.

## Ⅲ. Workflow Phases

The agent operates in a continuous loop through the following phases, as defined in `prompts/starter_prompt.txt`:

1.  **A. Fast Δ-Assessment (Delta Assessment)**:
    *   `scripts/qa_audit.py --mode=delta` is executed.
    *   If no Python code files have changed since the last audit, previous scores are reused.
    *   If code has changed, only the modified files are linted, type-checked, and tested. Quality axis deltas are computed.
    *   Results are appended to `prompts/quality_scoreboard.md` and `quality_scoreboard.json` is updated.
    *   A full baseline audit runs periodically (e.g., weekly) or when explicitly triggered.
    *   If all quality axes reach a perfect score (e.g., 100), the agent may halt or enter a monitoring state.

2.  **B. Roadmap Sync**:
    *   `scripts/roadmap_sync.py` (or equivalent logic) determines the active ticket from `prompts/roadmap.jsonl`.
    *   It performs a "rollover" if the previous ticket is complete:
        *   Marks the completed ticket as "DONE" in `roadmap.jsonl`.
        *   Sets the next appropriate ticket to "IN PROGRESS" in `roadmap.jsonl`.
        *   Rewrites the "Current ticket" section (§❸) in `prompts/starter_prompt.txt` with the new active ticket details and tasks.
        *   Incorporates lessons learned into the `starter_prompt.txt` guard-rail sections.

3.  **C. Implementation**:
    *   A new feature branch is created (e.g., `feature/<ticket-id>-<branch_slug>`).
    *   The agent follows a plan-code-test cycle for the tasks defined in the active ticket (from `starter_prompt.txt`).
    *   Includes self-critique and running `ruff --fix` and `pytest --cov <changed_files>`.
    *   If repeated failures occur (≥5 times for the same root cause), the agent stops and reports the issue for human intervention.

4.  **D. Review & Merge**:
    *   The agent automatically creates a Pull Request (PR) using the GitHub CLI. The PR body may include a summary of changes, including before/after quality axis scores.
    *   After human review and merge of the PR, the agent performs post-merge Git cleanup.

5.  **E. Logging**:
    *   A human-readable entry is appended to `prompts/development_log.md`.
    *   A structured JSONL entry is appended to an equivalent `development_log.jsonl`.

The agent then loops back to Phase A to begin the cycle anew.

## Ⅳ. Interaction with Human Developers

*   **Oversight & Intervention**: Humans review PRs generated by the agent and can intervene if the agent gets stuck or makes suboptimal decisions.
*   **Roadmap Definition**: Humans initially define the high-level roadmap and tasks in `prompts/roadmap.jsonl`. The agent primarily manages status updates and execution.
*   **Modifying Agent Behavior**: Changes to the agent's core logic, decision-making processes, or quality standards are made by editing the relevant prompt files (e.g., `starter_prompt.txt`, `codebase_review_prompt.txt`) or scripts.
*   **Debugging**: The generated logs (`development_log.md`, `quality_scoreboard.md`) and the structured nature of the prompts are intended to aid in debugging the agent's operations.

## Ⅴ. Current Status

This AI Agent Development Workflow is an active and integral part of the `ethereum_project`'s development process. It is continuously being refined. Contributors should be aware that the codebase and project state are influenced by this automated system.