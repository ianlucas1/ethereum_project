# Contributing
Welcome! Follow the steps below and your PR should sail through CI.

## 🔧 Local setup
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements-dev.txt
pre-commit install                 # auto-lints & sec-scans before every commit
```

## 🌳 Branch & PR flow

| Purpose | Prefix   | Example                |
| ------- | -------- | ---------------------- |
| Feature | `feat/`  | `feat/offchain-oracle` |
| Bug-fix | `fix/`   | `fix/outlier-division` |
| CI/docs | `chore/` | `chore/update-python`  |

1. **One logical change per PR**
2. Run tests: `pytest -q -n auto`
3. Pass local checks:

   ```bash
   bandit -r . --severity-level medium
   safety check --full-report
   ruff . --fix
   ```
4. Push & open PR:

   ```bash
   git push -u origin HEAD
   gh pr create --fill --label ci --base main
   ```

### Required checks

* `build`
* `lockfile`
* `CodeQL`
* `static-security` (Bandit & Safety)

## 🛠 Helpful CLI snippets

```bash
gh run list --limit 5 --json status,name,conclusion,url
gh run view --log \
  $(gh run list --limit 20 --json databaseId,conclusion \
     --jq "first([?conclusion=='failure']).databaseId") | tail -40
```

For deep config details see **docs/config-reference/** and `SECURITY.md`.

```

---
