# CI/CD Pipeline Details

The `ethereum_project` utilizes GitHub Actions for its Continuous Integration and Continuous Delivery (CI/CD) pipelines. These automated workflows ensure code quality, run tests, perform security scans, and can manage builds and deployments. This document details the key workflows found in `repo://.github/workflows/`.

Refer to the [CI/CD Overview Diagram](docs/architecture/ci_cd_overview.md) for a visual representation.

## Core Principles

*   **Automation:** Automate repetitive tasks like testing, linting, and building.
*   **Early Feedback:** Provide quick feedback to developers on pushes and pull requests.
*   **Consistency:** Ensure checks are run in a consistent environment.
*   **Security:** Integrate security scanning into the pipeline.
*   **Reproducibility:** Use locked dependencies for CI builds.

## Key Workflows

### 1. Main CI (`ci.yml`)
*   **Source:** `repo://.github/workflows/ci.yml`
*   **Triggers:** Runs on `push` and `pull_request` events to any branch.
*   **Purpose:** Acts as the primary CI check, covering testing, code coverage, and basic security scans.
*   **Jobs:**
    *   **`build`**:
        *   Environment: `ubuntu-latest`, Python `3.12`.
        *   Steps:
            1.  `actions/checkout@v4`: Checks out the repository code.
            2.  `actions/setup-python@v5`: Sets up the specified Python version.
            3.  Installs dependencies: `pip install -r requirements.txt -r requirements-dev.txt`. (Note: For stricter reproducibility, `requirements-lock.txt` would be better here if it includes all dev tools).
            4.  Runs tests: `pytest -q`.
            5.  `codecov/codecov-action@v4`: Uploads test coverage report to Codecov.io. `fail_ci_if_error: false` means a Codecov upload failure won't fail the CI job itself.
    *   **`bandit_safety`**:
        *   Environment: `ubuntu-latest`, Python `3.12`.
        *   Steps:
            1.  Checks out code.
            2.  Sets up Python.
            3.  Installs tools: `pip install bandit safety`.
            4.  Runs Bandit scan: `bandit -r . -s B101 -ll` (security linting, `-s B101` ignores `assert_used` warning, `-ll` reports medium severity and above).
            5.  Runs Safety scan: `safety check --full-report` (checks installed dependencies against a vulnerability database).
*   **Notes:** This workflow provides a good baseline. The `bandit_safety` job has some overlap with the dedicated `static-security.yml` and pre-commit hooks.

### 2. CodeQL Analysis (`codeql.yml`)
*   **Source:** `repo://.github/workflows/codeql.yml`
*   **Triggers:** Runs on `push` and `pull_request` to the `main` branch, and weekly on a schedule (`cron: '0 8 * * 1'`).
*   **Purpose:** Performs advanced static analysis using GitHub CodeQL to identify potential security vulnerabilities, bugs, and other code quality issues.
*   **Jobs:**
    *   **`analyze`**:
        *   Environment: `ubuntu-latest`, Python `3.12`.
        *   Steps: Checks out code, sets up Python, installs dependencies from `requirements.txt` (if exists), initializes CodeQL for Python, runs `autobuild` (CodeQL attempts to build the project to get better analysis), and then performs the CodeQL analysis. Results are typically shown in the "Security" tab of the GitHub repository.

### 3. Python CI (`python-ci.yml`)
*   **Source:** `repo://.github/workflows/python-ci.yml`
*   **Triggers:** Runs on `push` and `pull_request` to the `main` branch. Ignores paths like documentation (`**/*.md`, `docs/**`).
*   **Concurrency:** Uses `group: ${{ github.workflow }}-${{ github.ref }}` and `cancel-in-progress: true` to cancel older runs for the same branch/PR.
*   **Purpose:** Provides a focused Python testing environment with caching and parallel test execution.
*   **Jobs:**
    *   **`test`**:
        *   Environment: `ubuntu-latest` (matrix, though only one OS currently), Python `3.12`.
        *   Environment Variables: Sets dummy API keys (`RAPIDAPI_KEY: dummy`, `ETHERSCAN_API_KEY: dummy`) for tests that might expect them (mocks should handle these).
        *   Steps:
            1.  Checks out code.
            2.  Sets up Python.
            3.  Caches `pip` global cache and `pip wheels` based on `requirements-lock.txt` hash to speed up dependency installation.
            4.  Creates a virtual environment (`.venv`), activates it, upgrades pip, and installs dependencies from `requirements-dev.txt` (which should ideally be a superset or aligned with `requirements-lock.txt`).
            5.  Runs tests in parallel using `pytest -q -n auto` (requires `pytest-xdist`).

### 4. Docker Build Test (`docker-build.yml`)
*   **Source:** `repo://.github/workflows/docker-build.yml`
*   **Triggers:** Runs on `push` and `pull_request`.
*   **Purpose:** Verifies that the `repo://Dockerfile` is valid and the Docker image can be successfully built. It does not push the image to a registry.
*   **Jobs:**
    *   **`build`**:
        *   Environment: `ubuntu-latest`.
        *   Steps: Checks out code, sets up Python (for dependency caching used by Docker build layers if pip is run inside build), caches pip wheels, sets up Docker Buildx, and then builds the image using `docker/build-push-action`. `load: false` and `push: false` ensure the image is only built for validation.

### 5. Nightly Full Quality Audit (`nightly_audit.yml`)
*   **Source:** `repo://.github/workflows/nightly_audit.yml`
*   **Triggers:** Scheduled daily at 02:00 UTC (`cron: '0 2 * * *'`).
*   **Purpose:** Runs a custom comprehensive quality audit script and commits its results.
*   **Jobs:**
    *   **`audit`**:
        *   Environment: `ubuntu-latest`, Python `3.12`.
        *   Steps:
            1.  Checks out code.
            2.  Sets up Python.
            3.  Installs dev dependencies from `requirements-dev.txt`.
            4.  Runs the quality audit script: `python scripts/qa_audit.py --mode=full`.
            5.  Commits changes made by the script (to `prompts/quality_scoreboard.md`, `quality_scoreboard.json`, `.qa_audit_cache`) back to the repository using a `ci-bot` user.

### 6. Lockfile Consistency Check (`lockfile-check.yml`)
*   **Source:** `repo://.github/workflows/lockfile-check.yml`
*   **Triggers:** Runs on `push` and `pull_request`.
*   **Purpose:** Ensures that `repo://requirements-lock.txt` is up-to-date and consistent with `repo://requirements.txt`.
*   **Jobs:**
    *   **`lockfile`**:
        *   Environment: `ubuntu-latest`, Python `3.12` (with pip caching).
        *   Steps:
            1.  Checks out code.
            2.  Sets up Python.
            3.  Installs `pip-tools`.
            4.  Re-compiles `requirements-lock.txt` from `requirements.txt` using `pip-compile --quiet --output-file requirements-lock.txt requirements.txt`.
            5.  Uses `git diff --exit-code requirements-lock.txt` to check if the re-compiled lock file differs from the one committed. If there's a difference, the job fails, indicating the committed lock file is stale.
*   **Note:** This workflow focuses on `requirements.txt` -> `requirements-lock.txt`. A similar check or a combined compilation strategy might be needed for `requirements-dev.txt` and `requirements-runtime-lock.txt` to ensure full consistency across all requirement files if they are not all generated from a single pair of sources.

### 7. Static Security Scans (`static-security.yml`)
*   **Source:** `repo://.github/workflows/static-security.yml`
*   **Triggers:** Runs on `push`, `pull_request`, and weekly on schedule (`cron: '0 8 * * 1'`).
*   **Purpose:** Performs focused static security analysis using Bandit and Safety.
*   **Jobs:**
    *   **`static-security`**:
        *   Environment: `ubuntu-latest`, Python `3.12`.
        *   Steps:
            1.  Checks out code.
            2.  Sets up Python.
            3.  Caches pip dependencies.
            4.  Installs runtime dependencies (`requirements.txt`) plus `bandit` and `safety`.
            5.  Runs Bandit: `bandit -r . --severity-level medium` (fails on medium or higher severity issues).
            6.  Runs Safety: `safety check --full-report` (checks installed runtime dependencies for CVEs).

### 8. Python Nightly Full Matrix (`python-nightly-full-matrix.yml`)
*   **Source:** `repo://.github/workflows/python-nightly-full-matrix.yml`
*   **Triggers:** Scheduled daily at 00:00 UTC (`cron: '0 0 * * *'`).
*   **Concurrency:** `group: nightly-full-matrix`, `cancel-in-progress: true`.
*   **Purpose:** Runs the test suite across multiple operating systems to ensure broader compatibility.
*   **Jobs:**
    *   **`test`**:
        *   Strategy Matrix:
            *   OS: `ubuntu-latest`, `windows-latest`, `macos-latest`.
            *   Python Version: `3.12`.
            *   `fail-fast: false` ensures all jobs in the matrix complete even if one fails.
        *   Steps: Similar to `python-ci.yml`: checkout, setup Python for the matrix OS, cache pip & wheels, install dev dependencies from `requirements-dev.txt`, and run tests in parallel (`pytest -q -n auto`).

## Pre-commit Hooks

Complementing the GitHub Actions, `repo://.pre-commit-config.yaml` configures hooks that run locally before commits. This provides developers with immediate feedback on:
*   Code formatting (Ruff, Black)
*   Linting (Ruff, Flake8)
*   Import sorting (isort, or Ruff)
*   Static type checking (MyPy)
*   Basic security checks (Bandit)
*   Spell checking (Codespell)

This multi-layered approach to CI and local checks helps maintain a high standard of code quality, security, and reliability for the project. 