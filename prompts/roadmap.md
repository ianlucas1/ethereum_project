# updated roadmap.md

# ethereum_project · Roadmap
*(updated 2024-08-16)*

---

## 0 · Developer workflow (baseline)
* Conventional commits, pre-commit hooks, GitHub CI.
* Feature branches → PR → squash merge to **main**.
* All code passes: `pre-commit`, unit-tests, coverage ≥ 75 %, Docker build if present.

---

## 1 · Architecture & API hygiene  ✅ **DONE**
| Step | Detail | Status |
|------|--------|--------|
| 1.1 | Public API namespace flattened | ✓ |
| 1.2 | Settings via `pydantic.BaseSettings` | ✓ |
| 1.3 | FastAPI health-check endpoint | ✓ |

---

## 2 · Data-science leakage fixes  ✅ **DONE**
| Step | Detail | Status |
|------|--------|--------|
| 2.1 | Winsor leak fix | ✓ |
| 2.2 | Walk-forward split utility | ✓ |
| 2.3 | Stationarity test windowing | ✓ |

---

## 3 · Reliability & CI  ✅ **DONE (Gate C passed)**
| Step | Detail | Status |
|------|--------|--------|
| 3.1 | Retry/backoff wrapper | ✓ |
| 3.2 | Snapshot unit-tests | ✓ |
| 3.3 | GitHub Actions matrix (py 3.10-3.12) | ✓ |

---

## 4 · Maintainability & Dev-Experience  ✅ **DONE (Gate D passed)**

### 4.1 Pre-commit hook stack  ✅ DONE
### 4.2 Split `utils.py` ✅ DONE
### 4.3 Add Docker image ✅ DONE
### 4.4 Introduce `mypy --strict` ✅ DONE
| Step | Detail | Status |
|------|--------|--------|
| 4.4.1 | Add `mypy.ini` strict config | ✓ |
| 4.4.2 | Fix type errors in code-base | ✓ |
| 4.4.3 | Add `mypy` to pre-commit | ✓ |
| 4.4.4 | CI step for `mypy` | ✓ |
| 4.4.5 | Document any `type: ignore` | ✓ |
| 4.4.6 | Merge mypy-ignore docs PR | ✓ |

### 4.5 Replace raw `requests` with Session & global retry  ✅ **DONE**

---

## 5 · Documentation polish  ✅ **DONE (Gate E passed)**

### 5.1 Add docstrings and type hints ✅ **DONE**
| Step  | Detail                                                                       | Status |
|-------|------------------------------------------------------------------------------|--------|
| 5.1.1 | Add module-level docstrings to all `src/*.py` files.                         | ✓      |
| 5.1.2 | Add function/method docstrings (Google style) where missing or unclear.      | ✓      |
| 5.1.3 | Ensure all public functions/methods have type hints for args/return values.  | ✓      |
| 5.1.4 | Run `mypy` and `ruff check --select DOC` to verify.                          | ✓      |

---

## 6 · Testing & Coverage ✅ **DONE (Gate F passed)**

### 6.1 Increase Test Coverage to ≥ 75% ✅ **DONE**
| Step    | Detail                                                              | Status | Target Coverage |
|---------|---------------------------------------------------------------------|--------|-----------------|
| 6.1.1   | Write tests for `src/diagnostics.py`                                | ✓      | ≥ 75%           |
| 6.1.2   | Write tests for `src/data_fetching.py` (mocking APIs)               | ✓      | ≥ 75%           |
| 6.1.3   | Write tests for `src/ols_models.py`                                 | ✓      | ≥ 75%           |
| 6.1.4   | Write tests for `src/ts_models.py`                                  | ✓      | ≥ 75%           |
| 6.1.5   | Write tests for `src/data_processing.py`                            | ✓      | ≥ 75%           |
| 6.1.6   | Write tests for `src/validation.py`                                 | ✓      | ≥ 75%           |
| 6.1.7   | Improve tests for `src/eda.py`, `src/utils/*` if needed             | ✓      | ≥ 75%           |
| 6.1.8   | Verify overall coverage ≥ 75% using `coverage report`               | ✓      | ≥ 75%           |

---

## History (completed milestone gates)
| Gate | Date       | Notes                           |
|------|------------|---------------------------------|
| A    | 2025-02-10 | Baseline architecture validated |
| B    | 2025-03-05 | Leakage fixes validated         |
| C    | 2025-04-15 | Reliability suite + CI green    |
| D    | 2024-08-01 | Maintainability / DevX pass     |
| E    | 2024-08-16 | Documentation polish pass       |
| F    | 2024-08-17 | Testing & coverage pass         |

---

### Checkpoint (2024-08-17)
Testing & Coverage stream complete: **6.1 DONE** → Gate F passed.