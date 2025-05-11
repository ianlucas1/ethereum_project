# GitHub CLI Experimentation Plan  
*(updated 2025-05-11 after Run 4)*

This roadmap tracks experiments that probe an LLM agent's ability to manage a GitHub repository autonomously via the **`gh` CLI** (and, where needed, raw GitHub API calls).

---

## 📊 Status Dashboard  (🔥 = highest priority)

| Set | Focus (top experiment IDs)                           | Priority | Status |
|-----|------------------------------------------------------|----------|--------|
| 3   | Reacting to check status → re-run failed jobs (3-8)  | —        | **Done (Run 4)** |
| 4   | Info-extraction from failed checks (4-10/4-11)       | 🔥 High  | Pending |
| 5   | **Merge-queue & conflict handling** (5-1 ➜ 5-2)      | 🔥 High  | Pending |
| 6   | **Automatic remediation loop** (6-1 ➜ 6-2b)         | 🔥 High  | Pending |
| 9   | Context-window self-management (9-1)                 | ◼︎ Med+  | Pending |
| 8   | Dependabot autopilot (8-1 ➜ 8-2)                     | ◼︎ Med   | Pending |
| 10  | CI artifact retrieval / log consumption (10-1 ➜ 10-3)| 🔥 High  | Pending |
| 11  | Multi-PR queue awareness (11-1 ➜ 11-2)               | ◼︎ Med   | Pending |
| 7   | Secret-scanning push-protection (7-1 ➜ 7-2)          | ◻︎ Low   | Pending |
| 1,2 | Baseline PR & `gh pr checks` mechanics               | —        | Done |
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
| **5-1** | *Detect merge-queue block* | Open PR, then advance `main`; agent must notice GitHub's "out of date" / "needs update" message. |
| **5-2** | *Auto-rebase & re-push* | Agent rebases onto fresh `main`, force-pushes, watches CI re-run, merges when green. |

---

## **Experiment Set 6 — Automatic Remediation Loop**  🔥

| ID | Step | Goal |
|----|------|------|
| 6-1 | *Failing test already in repo* (2-5b) | PR #120 serves as the red baseline. |
| 6-2a | *Generate minimal fix* | Agent proposes a patch that makes the failing test pass. |
| 6-2b | *Apply fix & verify* | Push fix, ensure CI green, set auto-merge, branch deletes. |

---

## Experiment Set 7 — Secret-Scanning Push-Protection  ◻︎ Low

| ID | Step | Goal |
|----|------|------|
| 7-1 | *Intentionally push dummy secret* | Trigger server-side rejection. |
| 7-2 | *Auto-redact & re-push* | Agent removes secret, recommits, pushes successfully. |

---

## Experiment Set 8 — Dependency-Update Autopilot  ◼︎ Medium

| ID | Step | Goal |
|----|------|------|
| 8-1 | *Poll Dependabot PRs* | Detect open dependency PRs. |
| 8-2 | *Merge if green / open issue if red* | Close the loop on routine updates. |

---

## **Experiment Set 9 — Context-Window Self-Management**  ◼︎ Med+

| ID | Step | Goal |
|----|------|------|
| 9-1 | *Token-count monitor* | Log CoT token size; when > 30 k, write recap & truncate scratchpad. **Done (Run 5, Conceptual)** |

---

## **Experiment Set 10 — CI Artifact Retrieval**  🔥

| ID | Step | Goal |
|----|------|------|
| 10-1 | *Fetch log for failed job* | `gh run view <id> --log` **Done (Run 5)** |
| 10-2 | *Summarise traceback* | Natural-language 5-line summary. **Done (Run 5)** |
| 10-3 | *Tag failure class* | Code · Config · Infra · Flaky |

---

## **Experiment Set 11 — Multi-PR Queue Awareness**  ◼︎ Medium

| ID | Step | Goal |
|----|------|------|
| 11-1 | *List self-authored PRs* | `gh pr list --author` |
| 11-2 | *Cancel or update conflicting PR* | Avoid overlapping edits. |

---

## Back-burner Sets (no change)

*Set 5 (old)* — Diff-First workflow (JSON-only decision loop)  
*Set 6 (old)* — Model-swap efficiency study

---

### Time-Boxing Rule (unchanged)

> **20 minutes wall-clock or 3 hard failures → log attempts, mark "Partially Complete", move to next experiment.**

### Hygiene Rule (unchanged)

* Mini-summaries, chunked logs  
* Raw stdout/stderr goes into `github_cli_execution_log.md`  
* **No 4 000-token pause** — Agent must run uninterrupted.
* **Regular Integration:** Changes related to experiments or their documentation (plan, log, README updates) should be integrated frequently via a full PR cycle (branch, commit with passing hooks, push, PR, CI checks, merge, local cleanup). This avoids large, problematic accumulations of changes.

---

## Appendix A — Completed Experiment Sets

### Set 1 · PR Creation & Basic Inspection   ✅ *Finished Run 1*
*(see original RUN-1 report for raw outputs)*

### Set 2 · Deep Dive into `gh pr checks`   ✅ *Finished Run 2*
*(baseline pass/fail/pending parsing now proven reliable; no further work planned)*
