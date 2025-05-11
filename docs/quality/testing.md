# Testing Strategy

This document outlines the testing strategy employed in the `ethereum_project` to ensure code quality, correctness, and reliability. The project uses `pytest` as its primary testing framework.

## Guiding Principles

*   **Early Bug Detection:** Catch bugs as early as possible in the development cycle.
*   **Confidence in Refactoring:** Allow developers to refactor code with confidence that existing functionality remains intact.
*   **Documentation through Tests:** Tests serve as a form of executable documentation, illustrating how different parts of the system are intended to be used.
*   **Automation:** Testing is heavily automated and integrated into the CI/CD pipeline.

## Framework and Tools

*   **`pytest`**: The core testing framework. Chosen for its ease of use, powerful fixture system, and rich plugin ecosystem.
*   **`pytest-cov`**: Plugin for measuring code coverage.
*   **`pytest-xdist`**: Plugin for parallel test execution, speeding up the test suite.
*   **`unittest.mock`**: Python's built-in library (used extensively with `pytest`) for creating mock objects to isolate units of code during testing.
*   **`pandas.testing`**: Provides utilities like `assert_frame_equal` and `assert_series_equal` for robust comparison of pandas DataFrames and Series, crucial for this data-intensive project.

## Test Organization

*   **Location:** All tests are located in the `repo://tests/` directory at the root of the project.
*   **Structure:** The structure of the `tests/` directory generally mirrors the `repo://src/` directory. For example, tests for `src/data_processing.py` are found in `tests/test_data_processing.py`. This convention makes it easy to locate tests for specific modules.
*   **Naming Convention:** Test files are prefixed with `test_` (e.g., `test_example.py`). Test functions within these files are also prefixed with `test_` (e.g., `def test_something():`). `pytest` automatically discovers these.
*   **`conftest.py`**: The `repo://tests/conftest.py` file is used for defining shared `pytest` fixtures and hooks that are available to all tests in the `tests/` directory and its subdirectories. Currently, it primarily ensures that the `src` directory is added to `sys.path` for correct module imports during testing.

## Types of Tests

The project primarily focuses on **unit tests**, with some tests bordering on integration tests for specific data processing pipelines.

### 1. Unit Tests
*   **Focus:** Testing individual functions, methods, or classes in isolation.
*   **Methodology:**
    *   Dependencies of the unit under test (e.g., external API calls, file system operations, calls to other modules) are typically mocked using `unittest.mock.patch` and `unittest.mock.MagicMock`. This ensures that tests are fast, deterministic, and only test the logic of the unit itself.
    *   Examples:
        *   Testing a data transformation function in `src/data_processing.py` by providing a sample input DataFrame and asserting the output DataFrame's structure and values. External file loading within this function would be mocked.
        *   Testing an API call function in `src/utils/api_helpers.py` by mocking the `requests.get` call and asserting that the function processes the mock response correctly.
*   **Coverage:** Aim for high unit test coverage for all critical logic in `src/` modules.

### 2. Fixtures (`@pytest.fixture`)
*   **Purpose:** Pytest fixtures are heavily used to provide a fixed baseline for tests. They set up data, objects, or system states needed by one or more tests.
*   **Examples:**
    *   Creating sample pandas DataFrames representing raw or processed data (e.g., `sample_raw_core_df` in `repo://tests/test_data_processing.py`).
    *   Using built-in `pytest` fixtures like `tmp_path` (for creating temporary directories for tests involving file I/O) and `monkeypatch` (for safely modifying environment variables or object attributes at runtime for a test).

### 3. Scenario Coverage
Tests are designed to cover a variety of scenarios:
*   **"Happy Path":** Testing the expected behavior with valid inputs.
*   **Error Conditions:** Testing how functions handle invalid inputs, missing data, or expected exceptions (e.g., `FileNotFoundError`, `ValueError`, custom exceptions). `pytest.raises` is used to assert that specific exceptions are raised.
*   **Edge Cases:** Testing boundary conditions, empty inputs, zeros, NaNs, etc., especially important for numerical and data processing code.
*   **Specific Focus Areas:**
    *   **Utility Functions:** Dedicated tests for modules in `src/utils/` (e.g., `test_utils_cache.py`, `test_utils_file_io.py`).
    *   **Caching Logic:** Testing cache hits, misses, expiry, and data integrity for cached items.
    *   **Data Leakage:** Specific tests like `test_winsor_leak.py` and `test_stationarity_leak.py` aim to ensure that data processing steps do not inadvertently introduce lookahead bias or other forms of data leakage that would invalidate model results.
    *   **Snapshot Testing:** Some tests for API helpers (`test_utils_api_helpers_snapshot.py`) might use a form of snapshot testing where API responses are saved as fixtures and tests verify that the parsing logic correctly transforms these saved responses.

## Running Tests

1.  **Prerequisites:**
    *   Ensure the virtual environment (`.venv`) is activated.
    *   Ensure all development dependencies are installed (from `repo://requirements-lock.txt`).

2.  **Commands (from the project root):**
    *   **Run all tests:**
        ```bash
        pytest
        ```
    *   **Run tests with verbose output:**
        ```bash
        pytest -v
        ```
    *   **Run tests for a specific file:**
        ```bash
        pytest tests/test_data_processing.py
        ```
    *   **Run a specific test function by name (using `-k` expression):**
        ```bash
        pytest -k "test_load_raw_data_happy_path"
        ```
    *   **Run tests in parallel (requires `pytest-xdist`):**
        This is used in CI (`repo://.github/workflows/python-ci.yml`) via `pytest -q -n auto`.
        ```bash
        pytest -n auto  # 'auto' usually means one worker per CPU core
        ```
    *   **Run tests with code coverage report (console):**
        ```bash
        pytest --cov=src
        ```
    *   **Generate an HTML code coverage report:**
        ```bash
        pytest --cov=src --cov-report=html
        ```
        The report will be generated in the `htmlcov/` directory. Open `htmlcov/index.html` in a browser to view it.
    *   **Stop on first failure:**
        ```bash
        pytest -x
        ```

## Code Coverage

*   **Measurement:** Code coverage is measured using `pytest-cov`, which integrates with `coverage.py`.
*   **Target:** While a specific percentage is not strictly enforced as a hard gate, the project aims for high coverage of critical business logic.
*   **Reporting:**
    *   HTML reports can be generated locally for detailed inspection.
    *   In the CI pipeline (`repo://.github/workflows/ci.yml`), coverage data is uploaded to `Codecov.io` using the `codecov/codecov-action`. This allows tracking coverage trends over time and viewing coverage reports within pull requests.

## Integration with CI/CD

*   Tests are a fundamental part of the CI pipeline. Workflows like `ci.yml` and `python-ci.yml` execute the full test suite on every push and pull request.
*   A failing test suite will typically block merging of pull requests, ensuring that new changes do not break existing functionality.

This testing strategy aims to maintain a high level of quality and stability for the `ethereum_project`. 