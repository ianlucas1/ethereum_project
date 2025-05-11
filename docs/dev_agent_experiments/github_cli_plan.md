# GitHub CLI Experimentation Plan
*(updated 2025-05-11 after Run 4; Per-Run Log strategy note added)*

This roadmap tracks experiments that probe an LLM Agent's ability to manage a GitHub repository autonomously via the **`gh` CLI** (and, where needed, raw GitHub API calls). The Agent's actions, outputs, and learnings are recorded in separate log files for each experimental run (e.g., `github_cli_execution_log_RUN_X.md`).

---

## 📊 Status Dashboard  (🔥 = highest priority)

| Set | Focus (top experiment IDs)                           | Priority | Status |
|-----|------------------------------------------------------|----------|--------|
| 3   | Reacting to check status → re-run failed jobs (3-8)  | —        | **Done (Run 4)** |
| 4   | Info-extraction from failed checks (4-10/4-11)       | 🔥 High  | Pending |
| 5   | **Merge-queue & conflict handling** (5-1 ➜ 5-2)      | 🔥 High  | Pending |
| 6   | **Automatic remediation loop** (6-1 ➜ 6-2b)         | 🔥 High  | Pending |
| 9   | Context-window self-management (9-1)                 | ◼︎ Med+  | **Done (Run 5, Conceptual)** |
| 8   | Dependabot autopilot (8-1 ➜ 8-2)                     | ◼︎ Med   | Pending |
| 10  | CI artifact retrieval / log consumption (10-1 ➜ 10-3)| 🔥 High  | **Partially Done (Run 5: 10-1, 10-2)** |
| 11  | Multi-PR queue awareness (11-1 ➜ 11-2)               | ◼︎ Med   | Pending |
| 7   | Secret-scanning push-protection (7-1 ➜ 7-2)          | ◻︎ Low   | Pending |
| 1,2 | Baseline PR & `gh pr checks` mechanics               | —        | **Done (Run 1, Run 2/PR119 Logs)** |
| 12  | Custom Pre-commit & CI Policies (12-1 ➜ 12-3)        | ◼︎ Med   | **Done (Run 6)** |
| 5*  | Diff-first workflow (old)                            | —        | Back-burner |
| 6*  | Model-swap efficiency study (old)                    | —        | Back-burner |

> **Legend:** 🔥 High · ◼︎ Medium · ◻︎ Low · — Completed or deprioritised

---

## Experiment Set 3 — Reacting to Check Statuses  ✅ (Completed in Run 4)

*3-8* **Re-run failed CI checks** — implemented in Run 4 (PR #120, run-id 14957856078).  
*3-9* **Merge with failing checks** — Triggered in Run 5. Block detected & logged. **Done (Run 5)**

---

## Experiment Set 4 — Information Extraction from Failed Checks

*4-10* **Extract failing-check URLs** — baseline (`gh pr checks`).  
*4-11* **Fetch & summarise CI logs** — use `gh run view <id> --log`; write 5-line summary into execution log. **Done (Run 5)**

---

## **Experiment Set 5 — Merge-Queue & Conflict Handling**  🔥

| ID | Step | Goal |
|----|------|------|
| **5-1** | *Detect merge-queue block* | Agent to open PR, then Human Collaborator advances `main`; Agent must notice GitHub's "out of date" / "needs update" message on the PR. |
| **5-2** | *Auto-rebase & re-push* | Agent rebases PR branch onto fresh `main`, force-pushes, watches CI re-run, merges when green. |

---

## **Experiment Set 6 — Automatic Remediation Loop**  🔥

| ID | Step | Goal |
|----|------|------|
| 6-1 | *Failing test already in repo* (2-5b) | PR #120 serves as the red baseline. |
| 6-2a | *Generate minimal fix* | Agent proposes a patch that makes the failing test in PR #120 pass. |
| 6-2b | *Apply fix & verify* | Agent applies patch to PR #120's branch, pushes fix, ensures CI green, sets auto-merge, branch deletes. |

---

## Experiment Set 7 — Secret-Scanning Push-Protection  ◻︎ Low

| ID | Step | Goal |
|----|------|------|
| 7-1 | *Intentionally push dummy secret* | Agent attempts to push a commit containing a dummy secret, triggering server-side rejection. |
| 7-2 | *Auto-redact & re-push* | Agent identifies the problematic commit/file, removes/redacts the secret, amends the commit, and pushes successfully. |

---

## Experiment Set 8 — Dependency-Update Autopilot  ◼︎ Medium

| ID | Step | Goal |
|----|------|------|
| 8-1 | *Poll Dependabot PRs* | Agent uses `gh pr list` or API calls to detect open PRs authored by Dependabot. |
| 8-2 | *Merge if green / open issue if red* | If Dependabot PR has all green checks, Agent merges it. If checks are red, Agent opens a GitHub issue detailing the failure. |

---

## **Experiment Set 9 — Context-Window Self-Management**  ✅ (Completed in Run 5)

| ID | Step | Goal |
|----|------|------|
| 9-1 | *Token-count monitor* | Agent logs CoT token size; when > 30 k, writes recap & truncates scratchpad. **Done (Run 5, Conceptual)** |

---

## **Experiment Set 10 — CI Artifact Retrieval & Log Consumption**  🔥 (Partially Done)

| ID | Step | Goal |
|----|------|------|
| 10-1 | *Fetch log for failed job* | Agent uses `gh run view <id> --log` to retrieve logs for a specific failed job. **Done (Run 5, via Exp 4-11)** |
| 10-2 | *Summarise traceback* | Agent provides a natural-language 5-line summary of the key error/traceback from the fetched log. **Done (Run 5, via Exp 4-11)** |
| 10-3 | *Tag failure class* | Agent attempts to categorize the failure: Code Bug · Config Issue · Infrastructure Flake · Test Flakiness. |

---

## **Experiment Set 11 — Multi-PR Queue Awareness**  ◼︎ Medium

| ID | Step | Goal |
|----|------|------|
| 11-1 | *List self-authored PRs* | Agent uses `gh pr list --author "@me"` to list its own open PRs. |
| 11-2 | *Cancel or update conflicting PR* | If Agent creates a new PR that conflicts with one of its existing open PRs, it should identify the conflict and either close the old PR or update it to resolve the conflict. |

---

## Experiment Set 12 — Custom Pre-commit Hooks & CI Policies for Repo Hygiene ✅ (Completed in Run 6)

| ID    | Focus                                              | Priority | Status           |
|-------|----------------------------------------------------|----------|------------------|
| 12-1  | Add pre-commit hook to limit staged files (<25)      | ◼︎ Med   | **Done (Run 6)** |
| 12-2  | Add CI check for push frequency (>5 commits)         | ◼︎ Med   | **Done (Run 6)** |
| 12-3  | Refine README hygiene rules (log first, final sync)  | ◼︎ Med   | **Done (Run 6)** |

---

## Back-burner Sets (no change)

*Set 5 (old)* — Diff-First workflow (JSON-only decision loop)  
*Set 6 (old)* — Model-swap efficiency study

---

### Time-Boxing Rule (unchanged)

> **20 minutes wall-clock or 3 hard failures → Agent logs attempts, marks "Partially Complete", moves to next experiment.**

### Hygiene Rule (unchanged)

*   Mini-summaries, chunked logs by Agent.
*   Raw stdout/stderr goes into the active `github_cli_execution_log_*.md` file, not chat.
*   **No 4,000-token pause** — Agent must run uninterrupted, managing its own context if necessary (see Exp 9-1).
*   **Regular Integration (Log First!):** Changes related to experiments or their documentation (plan, log, README updates) MUST be logged by the Agent to the active `github_cli_execution_log_*.md` *before* being committed. The full cycle is: Experiment Actions -> Log Updates -> Commit (passing hooks) -> Push -> PR -> CI -> Merge -> Local Cleanup. This avoids out-of-sync logs and large, problematic change accumulations.
*   **Final Action of a Run (Log First!):** Before concluding a run, the Agent ensures all documentation is updated and all changes are pushed, merged via PR, and local git is tidied.

Refer to `docs/dev_agent_experiments/README.md` for the complete "Context-Hygiene Rules for the LLM Agent".

---

### Log File Management (Per-Run Logs)

To keep log files manageable, each distinct experimental "Run" by the Agent will typically use a new, uniquely named log file (e.g., `github_cli_execution_log_RUN_X.md`). The active log file for a given run will be confirmed at the start of that run. Refer to the main `README.md` for a complete list of hygiene rules.

---

## Appendix A — Completed Experiment Sets

### Set 1 · PR Creation & Basic Inspection   ✅ *Finished Run 1*
*(see original RUN-1 report or early logs for raw outputs)*

### Set 2 · Deep Dive into `gh pr checks`   ✅ *Finished Run 2 (via PR #119 log recovery)*
*(baseline pass/fail/pending parsing now proven reliable; pager issues addressed with `GH_PAGER=cat`)*