# GitHub CLI Experimentation Plan

This document outlines a series of experiments designed to test and document the capabilities and limitations of an LLM agent interacting with GitHub repositories using the GitHub Command Line Interface (`gh`).

## Experiment Set 1: PR Creation and Basic Inspection

1.  **Test: Create PR with Reviewers and Labels**
    *   **`gh` Command(s):** `gh pr create --title "Test PR for Advanced Checks" --body "Testing gh capabilities" --base main --head <test-branch> --reviewer <username1>,<username2> --label "test-suite","experiment"`
    *   **Capability Question:** How well do I parse and use information like assigned reviewers or labels in subsequent (simulated) decision-making?

2.  **Test: Create Draft PR**
    *   **`gh` Command(s):** `gh pr create --draft --title "Draft Test PR" --body "Testing draft PRs" --base main --head <another-test-branch>`
    *   **Capability Question:** Can I reliably identify a draft PR and understand that it might not be ready for checks or merging?

3.  **Test: List and Filter PRs**
    *   **`gh` Command(s):**
        *   `gh pr list --state open --author <my-bot-username-or-test-user>`
        *   `gh pr list --label "test-suite"`
        *   `gh pr list --state merged --limit 5`
    *   **Capability Question:** How effectively can I use filtering to find specific PRs relevant to a task?

## Experiment Set 2: Deep Dive into `gh pr checks` (Troubleshooting Focus)

*Pre-requisite for some tests below: A PR where some CI checks are designed to fail (e.g., by introducing a deliberate linter error or a failing test on the PR branch).*
***(High Priority)***

4.  **Test: `gh pr checks` - All Successful (Baseline)**
    *   **`gh` Command(s):** `gh pr checks <PR-number-with-all-passing-checks>`
    *   **Capability Question:** Confirm consistent parsing of successful outcomes.

5.  **Test: `gh pr checks` - One or More Failing Checks**
    *   **`gh` Command(s):** `gh pr checks <PR-number-with-failing-checks>`
    *   **Capability Questions:**
        *   Can I accurately parse the output to list *only* the failed checks and their log URLs?
        *   How robust is this parsing if the number or names of checks vary?

6.  **Test: `gh pr checks --watch` - Observing Transitions**
    *   **`gh` Command(s):** `gh pr checks <PR-number-with-initially-pending-or-failing-checks> --watch --interval 5` (run as background task)
    *   *Setup:* Trigger a re-run of checks or push a fix while `--watch` is active.
    *   **Capability Questions:**
        *   How well do I handle the streaming output of `--watch`?
        *   Can I set a "success" or "failure" condition to stop watching programmatically if the tool itself doesn't exit?

7.  **Test: `gh pr checks` - Checks in Progress/Pending**
    *   **`gh` Command(s):** `gh pr checks <PR-number-with-newly-pushed-commit-triggering-CI>`
    *   **Capability Question:** Can I differentiate between pending, successful, and failed states for each check?
***(High Priority)***

## Experiment Set 3: Reacting to Check Statuses
***(High Priority)***

8.  **Test: Attempting to Re-run Failed Checks**
    *   **`gh` Command(s):**
        *   `gh run list --workflow=<workflow-file.yml> --branch <pr-branch> --status failure` (to find run IDs)
        *   `gh run rerun <failed-run-id>`
        *   Alternatively: `gh api repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs --method POST`
    *   **Capability Questions:**
        *   How effectively can I identify the necessary `run-id` or `workflow-file.yml` from a PR context to trigger a re-run?
        *   Can I handle API calls with `gh api` if direct commands are insufficient?

9.  **Test: Merging a PR with Failing Checks (Understanding Safeguards)**
    *   **`gh` Command(s):** `gh pr merge <PR-number-with-failing-checks> --squash`
    *   **Capability Questions:**
        *   Can I correctly interpret the error message indicating that merge is blocked by failing checks?
***(High Priority)***

## Experiment Set 4: Information Extraction from Failed Checks

10. **Test: Extracting Log URLs from Failed Checks**
    *   **`gh` Command(s):** `gh pr checks <PR-number-with-failing-checks>`
    *   **Capability Questions:**
        *   Can I reliably extract *all* URLs associated with *failed* checks?
        *   **(Limitation Test):** Can I *access and interpret the content* of these URLs to find the root cause of the error? (Expected limitation).

## General Areas for Observation During All Experiments:

*   **Error Handling:** How are errors from `gh` reported and parsed?
*   **Non-Interactive Behavior:** Ensuring all commands run without interactive prompts.
*   **Dependency on Web UI:** Identifying when `gh` points to the web UI for further action.

## Experiment Set 5 – Diff-First Workflow (Medium)

1. **Goal:** Prove the Agent can raise a PR, validate CI, and merge *without ever parsing CLI stdout*—relying on Cursor's diff/context injection and MCP API calls instead.
2. **Steps:**
   * Use `@Branch` to generate summary and PR body.
   * Use MCP to open the PR and poll check-runs JSON.
   * Merge via MCP (or fall back to `gh pr merge`) once all checks are successful.
3. **Success metric:** zero pager errors; 100 % JSON-based decisions.

## Experiment Set 6 – Model-Swap Efficiency Study (Medium)

1. **Goal:** Quantify benefits of multi-model hand-offs on long-running watch/poll loops.
2. **Design:**
   * **Phase A:** Single-model (GPT-4 / o3) end-to-end run.
   * **Phase B:** Planner = Gemini 2.5; Executor = GPT-4.
3. **Metrics:** wall-clock time, token usage, number of human interventions, success rate. 