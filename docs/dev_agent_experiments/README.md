# Autonomous Development Agent Experiments

This document serves as a guide for the LLM Agent conducting autonomous development experiments, the Human Collaborator overseeing these experiments, and any future developers or LLMs seeking to understand this project. The term "Agent" herein refers to the LLM executing the experiments, and "Human Collaborator" refers to the user guiding the Agent.

────────────────────────────────────────────────────────
## Context-Hygiene Rules for the LLM Agent (Agent MUST follow)

1.  **Progressive summarisation**  
    • After each numbered experiment, the Agent will write a ≤ 5-line "Mini-Summary" at the end of its entry in the active `github_cli_execution_log_*.md` file.  
    • The Agent will **not** copy full CLI/stdout into chat; it will save it in the log file only.

2.  **Chunked logging**  
    • For multi-screen outputs, the Agent will fence them in the log and reference them by section (e.g., "see log §Exp 3-11 → Bandit output").  
    • Chat interactions should carry only high-level reasoning from the Agent.

3.  **Critical reminder scratchpad**  
    Before executing commands, the Agent will append this to its private scratchpad (not the repo):  
    > **Reminder**: `main` is protected → never push directly.  

4.  **Token guard (no hard pause)**  
    • If the Agent's chat context nears overflow, it will write a 1-paragraph recap in the active log file and **continue**; it will **not** halt at 4,000 tokens.  
    • The Agent will aim to keep active chat ≤ 2,000 tokens by summarising old reasoning.

5.  **Read-first contract**  
    *Before taking any action*, the *Agent* must read & absorb:  
    1. `github_cli_plan.md` (roadmap & experiment IDs)  
    2. The active `github_cli_execution_log_*.md` file for the current run (latest history)  
    3. `README.md` (this file)  

6.  **Time-boxing rule**  
    Each experiment gets **≤ 20 minutes or ≤ 3 failed attempts** by the Agent.  
    Exceeding this means: the Agent logs attempts, marks the experiment "Partially Complete", and moves on.

7.  **Regular Integration – Log First & Full Cycle:**
    • After every experiment or non-trivial documentation edit, the Agent MUST update the active `github_cli_execution_log_*.md` file with a comprehensive entry for the actions taken *before* committing any code or documentation changes.
    • The standard workflow for the Agent to integrate changes is: `Perform Actions -> Update Active Log File -> git add . -> git commit -> git push -> gh pr create -> Monitor CI -> gh pr merge -> Local Git Cleanup (checkout main, pull, delete feature branch).`
    • *Rationale*: This practice avoids large accumulations of unmerged changes and ensures logs are part of the PR, preventing an out-of-sync state post-merge. This was a key learning from PR #122 and PR #123 resolutions. For minor, purely documentation changes, these can sometimes be batched, but logging should still precede the commit of batched changes.

8.  **Final Action of a Run – Ensure Full Sync (Log First!):**
    • Before concluding an experiment run or a significant block of interaction, the Agent's *final actions* MUST be: 1) Update all relevant documentation (especially the active `github_cli_execution_log_*.md`). 2) Ensure these documentation changes AND any experimental code/config changes are committed, pushed, and merged via PR (after passing CI). 3) Perform local repository cleanup (switch to `main`, pull updates, and delete the local feature branch).
    • *Rationale*: This leaves the repository in a clean, synchronized, and documented state for future work or the next Agent session.

9.  **Per-Run Logging for Manageability:**
    • At the start of a new experimental run, a new, uniquely named log file will be designated (e.g., `github_cli_execution_log_RUN_X.md` or `github_cli_execution_log_YYYYMMDD_Topic.md`).
    • All logging for that run by the Agent will go into this new file. The specific name of the active log file will be confirmed at the beginning of the run.
    • *Rationale*: This keeps individual log files to a manageable size, preserving detail without creating unwieldy monolithic logs. An index or this README may point to the various log files.

Failure by the Agent to follow these rules counts as an experiment failure.
────────────────────────────────────────────────────────

## Purpose of these Experiments

This directory houses records and plans related to the "side quest" of enabling a frontier-level reasoning Large Language Model (LLM), the Agent, to operate as an increasingly autonomous development agent. The primary goal is to allow the Agent to further the development and refinement of the `ethereum_project` codebase, operating within the Cursor IDE.

These experiments are designed to:
- Systematically test and document the Agent's capabilities, particularly concerning Git version control, GitHub CLI (`gh`) interactions, and general shell command execution.
- Identify current limitations, points of confusion, or areas where the Agent's understanding or tooling access is insufficient.
- Refine the Agent's strategies for interacting with the development environment and managing common coding workflows.
- Explore the requirements for an LLM Agent to make autonomous decisions, such as merging pull requests, in a scenario where it is the sole "reviewer".

The ultimate aim is to improve the Agent's effectiveness and reduce the need for Human Collaborator intervention for routine development tasks.

## How to Use These Documents (For a Future LLM Agent)

If an LLM Agent is picking up this work, it should familiarize itself with the following:

1.  **This `README.md` file:** It provides the overarching context and hygiene rules for the Agent.
2.  **`github_cli_plan.md`:** This file contains the detailed, structured plan for experiments specifically focused on the GitHub CLI. It outlines tests that have been devised but may not have all been executed yet.
3.  **`github_cli_execution_log_*.md` files:** These are critical files. There may be multiple log files, one for each distinct experimental "Run" (e.g., `github_cli_execution_log_RUN_X.md`). The specific active log file for the Agent's current run should be confirmed. They contain a chronological record of experiments performed by previous Agent instances or iterations, including:
    *   The Agent's reasoning *before* taking an action (Chain of Thought - CoT).
    *   The exact command(s) executed.
    *   The raw output from those commands.
    *   The Agent's analysis and interpretation of the results *after* the action (Post-Action CoT).
    *   Specific learnings, reflections, or newly identified questions.

To continue the work, the Agent should:
- Review the `github_cli_plan.md` to understand pending experiments.
- Review the relevant `github_cli_execution_log_*.md` files to see what has been accomplished, what issues were encountered, and the latest state of understanding.
- Continue executing planned experiments or devise new ones based on previous findings, always maintaining the logging format in the active execution log file and adhering to the practice of regular, full-cycle integration of changes.

## Collaboration with Human Collaborator (You!)

A key aspect of these experiments is collaboration between the Agent and the Human Collaborator. The LLM Agent operates within a specific environment (Cursor IDE, specific shell setup) which may have its own nuances.

**Crucially, if the Agent documents in the active `github_cli_execution_log_*.md` that it was unable to obtain expected results from a CLI command or API query (e.g., due to output parsing issues, unexpected errors, or apparent environmental differences), it will explicitly request *you, the Human Collaborator*, to:**
1.  Run the *exact same command* in your own terminal environment (e.g., Cursor's built-in terminal or your system terminal).
2.  Provide the complete, raw output back to the Agent via the chat interface.

This collaborative troubleshooting is vital for distinguishing between the Agent's inherent limitations and environmental factors, and for finding workarounds. Assistance from the Human Collaborator in these cases is invaluable for the progress of this experimental "side quest".

## Agent Learnings: Navigating Pre-commit Hooks and CI Interactions

Recent experiments, particularly the process of committing and merging PR #122 which involved numerous pre-existing linting and formatting issues, highlighted several key challenges and effective strategies for an autonomous Agent interacting with repositories that use strict pre-commit hooks (especially auto-formatters like `black` and linters like `flake8`).

### Key Challenges Observed by the Agent:

1.  **Formatter vs. Linter Conflicts:** Auto-formatters (`black`, `isort`) can reformat code in ways that subsequently trigger linters (`flake8` for line length - E501, `codespell`). The Agent found that attempting to fix linter issues can be undone by the formatter on the next commit attempt.
2.  **Ineffective `noqa` Comments:** If linters are run after formatters have already altered the line (or moved the `noqa` comment), the Agent observed that the ignore directive may not apply correctly.
3.  **Persistent Minor Errors:** Some errors (e.g., a single `codespell` issue) proved surprisingly resilient to automated fixes by the Agent if formatters subtly changed the line content or structure around the fix.
4.  **Local State Management:** Pre-commit hooks modifying files locally can lead to an "unclean" working directory, which the Agent found can interfere with subsequent git operations like `git checkout` or `gh pr merge` (which attempts local branch cleanup).

### Effective Strategies and Learnings for Agents:

1.  **Establish a Formatted Baseline (`git commit --no-verify`):**
    *   When facing many hook failures, especially from formatters, a crucial first step for the Agent can be to commit all intended changes using `git commit --no-verify`. This bypasses hooks and establishes a stable, auto-formatted version of the code as the baseline for subsequent targeted fixes.
    *   *Caution*: This should be used judiciously by the Agent, typically on a feature branch it controls, and the intention should be to follow up immediately with fixes to satisfy the hooks.

2.  **Targeted Linter/Hook Execution:**
    *   After establishing a baseline, the Agent should run specific pre-commit hooks (e.g., `pre-commit run flake8 --all-files`) to get an accurate list of outstanding issues on the *formatted* code. This avoids chasing errors on lines that formatters will change anyway.

3.  **Handling Widespread Stylistic Linter Errors (e.g., E501):**
    *   **`# noqa: <ERROR_CODE>`:** For linter errors (like `flake8` E501) on lines that `black` insists on formatting in a particular (long) way, the Agent learned the most precise solution is to append `# noqa: E501` to the *exact* line flagged by the linter *after* `black` has formatted it. This requires careful identification of the line post-formatting.
    *   **CI Configuration Adjustment:** If numerous stylistic errors (that don't affect code functionality) are blocking progress and are difficult for an Agent to resolve perfectly against an aggressive formatter, a pragmatic solution can be to adjust the CI linter configuration to be more permissive (e.g., adding E501 to `flake8`'s ignore list in the CI workflow). This should align with project standards or be a temporary measure, ideally confirmed with the Human Collaborator.

4.  **Iterative Commits with `--amend`:**
    *   When fixing hook issues iteratively, the Agent should use `git commit --amend` to keep the feature branch history clean, rather than creating many small, incremental fixup commits.

5.  **Force Pushing Amended Commits (`git push --force`):**
    *   If a branch has already been pushed and its history is then changed by the Agent (e.g., by amending commits), `git push --force` will be necessary. This should be done with caution, primarily on feature branches not yet merged or widely used by others.

6.  **Managing Local Changes from Hooks (`git stash`):**
    *   If git operations like `checkout` or `merge` (with local cleanup) fail due to uncommitted changes left by pre-commit hooks, the Agent should use `git stash` to temporarily shelve these changes. After the primary git operation is complete, the stash can be inspected, applied, or dropped.

7.  **Local Branch Cleanup After Squash Merges (`git branch -D`):**
    *   When a PR is squash-merged on the Git remote (e.g., via GitHub UI or `gh pr merge --squash`), the local feature branch will not be seen as "fully merged" by a simple `git branch -d`. The Agent learned that a force delete (`git branch -D <branch_name>`) is typically required.

8.  **Persistence for Minor Errors:**
    *   The Agent observed that sometimes, a minor error (like the persistent `codespell` issue) might resolve after several cycles of formatting and commit attempts. The exact cause might be an interplay of tool versions or subtle formatting changes. The Agent should ensure the final verified commit passes all critical hooks.

By employing these strategies, an LLM Agent can more robustly navigate complex pre-commit and CI environments, moving closer to autonomous repository management.