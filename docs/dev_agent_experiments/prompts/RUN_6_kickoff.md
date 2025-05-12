You are the autonomous GitHub-CLI agent continuing **Run 6** in `ianlucas1/ethereum_project`.

──────────────────── Phase A · Maintenance ────────────────────
**0.a Archive legacy run‑analysis reports**  
* **Stage untracked reports / CoT files first**  
  ```bash
  git add docs/dev_agent_experiments/analysis_of_autonomous_* \
          docs/dev_agent_experiments/*CoT\ Message\ History.txt || true
  ```

* Make directory `docs/dev_agent_experiments/archive/reports` (if absent) and move the analysis reports:

  ```bash
  mkdir -p docs/dev_agent_experiments/archive/reports
  git mv docs/dev_agent_experiments/analysis_of_autonomous_github_cli_experiments_RUN-* \
         docs/dev_agent_experiments/archive/reports/
  ```
* Commit with message `chore: archive legacy RUN analysis reports`.

**0.b Persist kickoff prompt**

* Path: `docs/dev_agent_experiments/prompts/RUN_6_kickoff.md`
* Copy the exact contents of this chat prompt into that file, commit, and push.
* Append to **README Rule 5** (Read‑first contract):
  `4. docs/dev_agent_experiments/prompts/RUN_<N>_kickoff.md (the active run's kickoff instructions).`

**1. Bootstrap environment script**

* Create `scripts/agent_env.sh` with:

  ```bash
  #!/usr/bin/env bash
  export GH_PAGER=cat
  export LESS=F
  ```
* Commit the script (it will be reused in future runs).

**2. Environment prep**  
   ```bash
   source scripts/agent_env.sh
   gh --version && echo $GH_PAGER   # verify pager vars
   ```

**3. 12-4 Hook-Guard repair + self-test**

* File: `.github/workflows/hook-guard-test.yml`
* Fix logic so a one-file PR passes.
* Add job **hook-guard-selftest**: matrix `{files:[1,30]}` → generate N dummy files, commit, expect **success** for 1, **failure** for 30.
* Merge only after CI passes **and** self-test proves behaviour.
* After merge, delete temp self-test branches (`git push origin --delete <branch>`).

**4. Per-run logging switch (12-5)**

* Create `docs/dev_agent_experiments/github_cli_execution_log_RUN_6.md`.
* Move legacy log to `docs/archive/github_cli_execution_log_legacy.md`.
* Update **README Rule 9** and examples in `github_cli_plan.md` to point to the new file.

**5. Pre-commit parity check**

* On clean `main` run `pre-commit run --all-files`.
* If any hook fails, open a quick fix PR before other work.

**6. Plan/dashboard sync** (`github_cli_plan.md`)

* Mark: Set 10 = Done; Sets 5 & 6 = Partially Complete.
* Add rows: **12-4**, **12-5**, and Set 13 skeleton (13-1/13-2).
* Append branch-naming convention to README Rule 5: `experiment/run6-<task-id>-<slug>`.

**7. Clean stale artifacts**

* Close PR #134 and delete its local **and** remote branches.
* Ensure no other open agent PRs (`gh pr list --author "@me" --state open`).

──────────────────── Phase B · Experiments ────────────────────

| Set | ID                 | Branch template                    | Purpose                                                                                                                                                    |
| --- | ------------------ | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5   | **5-2-retry**      | `experiment/run6-5-2-rebase-merge` | Auto-rebase & re-push PR #133 (or successor) after Guard fix; merge when green                                                                             |
| 6   | **6-2b-retry**     | `experiment/run6-6-2b-fix-test`    | Rebase `experiment/2-5b-failing-test` on latest `main`, resolve **doc conflicts preferring main content unless branch adds new lines**, then merge PR #120 |
| 11  | 11-1 → 11-2 (opt.) | `experiment/run6-11-pr-triage`     | Post-merge PR queue cleanup                                                                                                                                |
| 13  | 13-1, 13-2 (opt.)  | `experiment/run6-13-quick-wins`    | 13-1: add Severity × Frequency table to README; 13-2: map hygiene rules ↔ design principles                                                                |

──────────── Post-merge validation ────────────

* After Hook-Guard merge, trigger **hook-guard-selftest** on `main`; ensure 1-file case passes, 30-file fails.
* After each PR merge, verify guard status:

  ```bash
  gh run list --branch <PR-branch> --workflow "Hook Guard"
  ```
* Run `pre-commit run --all-files` on updated `main`; open a fix PR if new failures surface.

──────────── Guardrails ────────────

* **Read-first:** `docs/dev_agent_experiments/README.md`, `github_cli_plan.md`, `github_cli_execution_log_RUN_6.md`, `prompts/RUN_6_kickoff.md`.
* **Hygiene:** ≤ 5-line mini-summaries, chunked logs, no hard pauses.
* **Time-box:** ≤ 20 min or ≤ 3 failed attempts per task.
* **Log-first cycle:** update RUN 6 log → `git add` → `git commit -m "feat: …"` → `git push` → `gh pr create` → `gh pr checks --watch` → merge → tidy branches.
* **Branch naming:** use template `experiment/run6-<task-id>-<slug>`; delete local **and** remote branches after PRs close/merge.
* **Exact refs:** PR #120, workflow `.github/workflows/hook-guard-test.yml`, failing run ID 14962854869.
* **Fallback:** after max retries, log reason, mark experiment *Partially Complete*, proceed. 