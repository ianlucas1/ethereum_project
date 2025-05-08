# Project Configuration Details for LLM Context

This document consolidates the content of various configuration files in the project. It is intended to provide comprehensive context to Large Language Models.

## `.gitignore`

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environment
.venv/
venv/
ENV/
env/
*/.venv/
*/venv/
*/ENV/
*/env/

snapshots/

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
# Usually these files are written by a python script from a template
# before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# PEP 582; used by PDM, PEP 582 compatible tools and project workflow
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.env.*
env.yaml

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static analysis results
.pytype/

# Cython debug symbols
cython_debug/

# VS Code settings specific to this project
.vscode/

# Cursor / IDX specific
.idx/

# --- Project-specific Generated Outputs, Data, and Cache ---
# Ignore all contents of the data directory by default
data/

# Specific patterns for generated data/output files (mostly within data/)
data/*.parquet
data/*.csv
final_results.json
raw_core_data_plot.png

# Cache lock files (often in data/)
data/*.lock
data/*.tmp

# Project-specific cache files
.qa_audit_cache

# OS generated files
.DS_Store
Thumbs.db

type_ignore_occurrences.txt

# ... other ignores ...
cycle_summary_latest.md.ci-venv/
```

## `.pre-commit-config.yaml`

```yaml
# .pre-commit-config.yaml
repos:
  # --------------------------------------------------------------------- #
  # Ruff (formatter + linter) — keep version in sync with requirements     #
  # --------------------------------------------------------------------- #
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.0.241            # ruff==0.0.241 in requirements-dev.txt
    hooks:
      - id: ruff             # does both linting & formatting
        args: [--fix, --exit-non-zero-on-fix]   # auto-fix and fail if fixes made

  # --------------------------------------------------------------------- #
  # Flake8 — extra opinionated linting (Ruff already covers most rules)    #
  # --------------------------------------------------------------------- #
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies:
          - flake8-bugbear>=23.9.16
        args:
          - --max-line-length=88
          - --ignore=E203,E501,W503

  # --------------------------------------------------------------------- #
  # MyPy strict static type-checking                                        #
  # --------------------------------------------------------------------- #
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0                 # keep in sync with requirements-dev.txt
    hooks:
      - id: mypy
        name: mypy (strict)
        pass_filenames: false     # run once; MyPy discovers files itself
        additional_dependencies:
          - "mypy==1.15.0"
          - "pydantic>=1.10,<2"   # v1 plugin only
          - "types-requests"      # silence requests import
        args:
          - "--config-file"
          - "mypy.ini"
          - "src"
```

## `.python-version`

```
3.11
```

## `.dockerignore`

```dockerignore
# Python byte-code / caches
__pycache__/
*.py[cod]

# Virtual-envs & local tooling
.venv/
.mypy_cache/
.pytest_cache/

# Data & artifacts
data/
snapshots/
*.parquet
*.csv
*.feather

# Git & CI metadata
.git
.github

# OS / editor noise
.DS_Store
```

## `mypy.ini`

```ini
# mypy strict configuration for ethereum_project
#
# * 'strict = True' enables the full set of extra checks
# * Third-party stub noise is silenced globally for now
# * Every future  # type: ignore  must include a justification

[mypy]
python_version        = 3.11
strict                = True
show_error_codes      = True
pretty                = True
warn_unused_ignores   = True

# third-party libs often ship without stubs
ignore_missing_imports = True
disable_error_code     = import, attr-defined, import-untyped

plugins               = pydantic.mypy

# completely skip these directories
exclude               = ^(?:\.venv|\.git|build|docs|scripts|tests)/

[pydantic-mypy]
init_typed                    = true
warn_required_dynamic_aliases = true

# ── Module-specific overrides ──────────────────────────────────────────
[mypy-tests.*]
ignore_errors  = True
follow_imports = skip

[mypy-src.eda]
# display() signature hacks
ignore_errors = True

[mypy-src.data_fetching]
ignore_errors = True

[mypy-src.utils.api_helpers]
ignore_missing_imports = True
```

## `pip.conf`

```ini
[global]
extra-index-url = https://pypi.fury.io/arrow-nightlies/
```

## `.github/workflows/ci.yml` (General CI)

```yaml
name: Python CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12"]  # test across supported versions

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: requirements-lock.txt

      # ---------- dependency install ---------------------------------------------------------
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-lock.txt
          pip install pytest-cov

      # ---------- lint -----------------------------------------------------------------------
      - name: Lint with Ruff (optional, good practice)
        run: |
          pip install ruff==0.0.241      # same version used in local dev hooks
          ruff .                         # no --check flag in this version

      # ---------- tests ----------------------------------------------------------------------
      - name: Test with pytest and generate coverage report
        if: matrix.os != 'macos-latest' || matrix.python-version == '3.10'
        env:
          RAPIDAPI_KEY: dummy_key_for_ci
          CM_API_KEY: ""
          ETHERSCAN_API_KEY: ""
        run: pytest --cov=src --cov-report=xml

      - name: Test with pytest (no coverage)
        if: matrix.os == 'macos-latest' && matrix.python-version != '3.10'
        env:
          RAPIDAPI_KEY: dummy_key_for_ci
          CM_API_KEY: ""
          ETHERSCAN_API_KEY: ""
        run: pytest -q

      # ---------- coverage upload ------------------------------------------------------------
      - name: Upload coverage reports to Codecov
        if: matrix.os != 'macos-latest' || matrix.python-version == '3.10'
        uses: codecov/codecov-action@v4.0.1
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          slug: ${{ github.repository }}
          fail_ci_if_error: true
```

## `.github/workflows/python-ci.yml` (Main Branch Focused CI)

```yaml
name: Python CI

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

on:
  push:
    branches: [main]
    paths-ignore:
      - '**/*.md'
      - '**/*.txt'
      - 'docs/**'
      - 'roadmap.md'
  pull_request:
    branches: [main]
    paths-ignore:
      - '**/*.md'
      - '**/*.txt'
      - 'docs/**'
      - 'roadmap.md'

jobs:
  test:
    runs-on: ${{ matrix.os }}
    env:
      RAPIDAPI_KEY: dummy
      ETHERSCAN_API_KEY: dummy

    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.11']

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ runner.os }}-${{ hashFiles('requirements-lock.txt') }}
          restore-keys: pip-${{ runner.os }}-

      - name: Cache pip wheels
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip/wheels
          key: wheels-${{ runner.os }}-${{ hashFiles('requirements-lock.txt') }}
          restore-keys: wheels-${{ runner.os }}-

      - name: Cache virtualenv
        uses: actions/cache@v4
        with:
          path: .venv
          key: venv-${{ runner.os }}-${{ hashFiles('requirements-lock.txt') }}
          restore-keys: venv-${{ runner.os }}-

      - name: Set up virtualenv & install deps (only on cache miss)
        run: |
          if [ ! -d ".venv" ]; then
            python -m venv .venv
            . .venv/bin/activate
            python -m pip install --upgrade pip
            pip install -r requirements-dev.txt
          fi

      - name: Run tests in parallel
        run: .venv/bin/pytest -q -n auto
```

## `.github/workflows/python-nightly-full-matrix.yml`

```yaml
name: Python CI Full Matrix Nightly

on:
  schedule:
    - cron: '0 0 * * *'

concurrency:
  group: nightly-full-matrix
  cancel-in-progress: true

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']
      fail-fast: false

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ runner.os }}-${{ hashFiles('requirements-lock.txt') }}
          restore-keys: pip-${{ runner.os }}-
      - name: Cache pip wheels
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip/wheels
          key: wheels-${{ runner.os }}-${{ hashFiles('requirements-lock.txt') }}
          restore-keys: wheels-${{ runner.os }}-
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      - name: Run tests in parallel
        run: pytest -q -n auto
```

## `.github/workflows/docker-build.yml`

```yaml
name: Docker build (4.3.4)

on:
  pull_request:
    branches: [ "**" ]
    paths:
      - "Dockerfile"
      - ".dockerignore"
      - "requirements*.txt"
      - "src/**"
      - "tests/**"
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      # -- optional wheel-cache speeds up pip layer
      - name: Set up Python for dependency caching
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache pip wheels
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image (no push)
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          tags: ethereum_project:test
          load: false         # don't load into local Docker daemon
          push: false