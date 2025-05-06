# Ethereum Econometric Valuation Analysis

## Overview

This project conducts an econometric analysis of Ethereum (ETH) valuation, primarily exploring its relationship with network activity metrics, drawing inspiration from Metcalfe's Law. It aims to identify key drivers of ETH's value using various statistical models. The project fetches, processes, and analyzes on-chain and market data for Ethereum and benchmark assets like the NASDAQ index.

The primary execution script is `main.py`, which runs the complete end-to-end analysis pipeline. For interactive data exploration, model development, and visualization, `research.py` provides a suitable environment.

## Key Features

*   **Data Fetching**: Retrieves on-chain data (e.g., active addresses, transaction counts) and market data (prices, volumes) from various APIs.
*   **Data Processing**: Cleans, transforms, merges, and resamples raw data into daily and monthly frequencies suitable for analysis.
*   **Exploratory Data Analysis (EDA)**: Includes outlier treatment (e.g., winsorization) and stationarity testing (e.g., ADF tests) on time series data.
*   **Econometric Modeling**: Implements and evaluates several models:
    *   Ordinary Least Squares (OLS) benchmarks.
    *   Vector Error Correction Models (VECM).
    *   Autoregressive Distributed Lag (ARDL) models.
*   **Model Diagnostics**: Performs residual analysis and structural break tests.
*   **Out-of-Sample Validation**: Conducts rolling window validation to assess model robustness.
*   **Reporting**: Generates a structured JSON file (`final_results.json`) with all analysis results and prints a summary interpretation.

## Technology Stack

*   **Language**: Python
*   **Core Libraries**:
    *   `pandas` (for data manipulation)
    *   `numpy` (for numerical operations)
    *   `statsmodels` (for statistical models, e.g., OLS, ARDL, VECM diagnostics)
    *   `linearmodels` (for panel data models, though primary use here is for advanced time series models)
    *   `scikit-learn` (for utility functions like preprocessing)
    *   `matplotlib` & `seaborn` (for data visualization)
    *   `requests` (for API communication)
    *   `pydantic` (for configuration management)
    *   `pyarrow` (for efficient Parquet file handling)
*   **Containerization**: Docker
*   **Development Tools**: (Detailed in `PROJECT_CONFIG_DETAILS.md`)
    *   `pre-commit` (for git hooks)
    *   `ruff` & `flake8` (for linting and formatting)
    *   `mypy` (for static type checking)
    *   `pytest` (for testing)

## Project Structure

```
ethereum_project/
├── .git/                        # Git repository data
├── .github/                     # GitHub Actions workflows (CI/CD)
├── .venv/                       # Python virtual environment (user-created)
├── data/                        # Raw and processed data files (e.g., .parquet)
├── docs/                        # Project documentation (e.g., type ignore guidelines)
├── htmlcov/                     # HTML code coverage reports
├── scripts/                     # Utility scripts (if any)
├── src/                         # Core source code
│   ├── utils/                   # Utility modules (caching, API helpers, file I/O)
│   ├── __init__.py
│   ├── config.py                # Project configuration (loads .env)
│   ├── data_fetching.py         # Data retrieval logic
│   ├── data_processing.py       # Data cleaning, transformation, feature engineering
│   ├── diagnostics.py           # Model diagnostic tests
│   ├── eda.py                   # Exploratory Data Analysis functions
│   ├── main.py                  # Main pipeline script (moved to root in your project)
│   ├── modeling.py              # (Currently minimal, core models in dedicated files)
│   ├── ols_models.py            # OLS regression models
│   ├── reporting.py             # Results summarization and output generation
│   ├── ts_models.py             # Time series models (VECM, ARDL)
│   └── validation.py            # Out-of-sample validation logic
├── tests/                       # Automated tests
├── .dockerignore                # Specifies files to exclude from Docker builds
├── .gitignore                   # Specifies intentionally untracked files for Git
├── .pre-commit-config.yaml      # Configuration for pre-commit hooks
├── .python-version              # Specifies the project's Python version (e.g., for pyenv)
├── Dockerfile                   # Defines the Docker image for the project
├── final_results.json           # Output JSON from the analysis pipeline
├── LICENSE                      # Project license information
├── main.py                      # Main script to run the full analysis pipeline
├── mypy.ini                     # Configuration for mypy static type checker
├── pip.conf                     # pip configuration (e.g., extra index URLs)
├── PROJECT_CONFIG_DETAILS.md    # Detailed content of hidden config files for LLM context
├── raw_core_data_plot.png       # Example diagnostic plot
├── README.md                    # This file
├── research.py                  # Script for interactive research and plotting
├── requirements-dev.txt         # Dependencies for development (linters, testers)
└── requirements-lock.txt        # Pinned versions of all dependencies for reproducible environments
```

## Modules (`src/` directory)

*   `config.py`: Manages project settings and API keys, primarily by loading them from an `.env` file.
*   `data_fetching.py`: Handles fetching raw data from external APIs (e.g., CoinMetrics, Yahoo Finance), including caching mechanisms.
*   `data_processing.py`: Cleans, transforms, merges, and resamples raw data into analysis-ready `daily_clean.parquet` and `monthly_clean.parquet` datasets.
*   `diagnostics.py`: Implements model diagnostic tests, such as residual analysis and structural break tests.
*   `eda.py`: Provides functions for exploratory data analysis, including data winsorization and stationarity tests (e.g., ADF).
*   `modeling.py`: Currently a minimal file; core modeling logic is in `ols_models.py` and `ts_models.py`.
*   `ols_models.py`: Implements Ordinary Least Squares (OLS) benchmark models.
*   `reporting.py`: Generates summaries of analysis results, formats them into a structured dictionary, and handles JSON serialization.
*   `ts_models.py`: Implements time series models like Vector Error Correction Models (VECM) and Autoregressive Distributed Lag (ARDL) models.
*   `validation.py`: Handles out-of-sample model validation, particularly rolling window validation, ensuring preprocessing steps are applied correctly within each window to prevent data leakage.
*   `utils/`: A sub-package containing various utility modules:
    *   `cache.py`: Caching utilities.
    *   `api_helpers.py`: Helper functions for interacting with external APIs.
    *   `file_io.py`: Utilities for file input/output.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd ethereum_project
    ```

2.  **Ensure Correct Python Version:**
    *   The project is configured to use **Python 3.11** for local development, as specified in the `.python-version` file (used by tools like `pyenv`).
    *   The `Dockerfile` uses **Python 3.12-slim** for containerized execution.
    *   Ensure you have Python 3.11 accessible for local work. Check with `python --version` (if `pyenv` is active) or `python3.11 --version`.

3.  **Create and Activate Virtual Environment (using Python 3.11):**
    ```bash
    # Using Python 3.11
    python3.11 -m venv .venv

    # Activate on macOS/Linux:
    source .venv/bin/activate
    # Activate on Windows (Git Bash):
    # source .venv/Scripts/activate
    ```
    Ensure `.venv/` is in your `.gitignore`.

4.  **Install Dependencies:**
    Install the exact dependencies from the lock file for a reproducible environment:
    ```bash
    pip install --upgrade pip
    pip install -r requirements-lock.txt
    ```

5.  **Developer Dependencies (Optional):**
    For development (running linters, type checkers, tests locally):
    ```bash
    pip install -r requirements-dev.txt
    ```
    It's recommended to set up `pre-commit` hooks:
    ```bash
    pre-commit install
    ```

6.  **Environment Variables (`.env` file):**
    Create a `.env` file in the project root for API keys and other configurations. `src/config.py` loads these variables.
    Example `.env` content:
    ```dotenv
    RAPIDAPI_KEY=your_rapidapi_key_here
    CM_API_KEY=your_coinmetrics_key_here # Optional
    ETHERSCAN_API_KEY=your_etherscan_key_here # Optional
    ```
    Ensure `.env` is listed in your `.gitignore` file.

## Usage

### Full Pipeline Execution

1.  Activate your virtual environment (e.g., `source .venv/bin/activate`).
2.  Ensure required environment variables (at least `RAPIDAPI_KEY`) are set in your `.env` file or system environment.
3.  Run `main.py` from the project root:
    ```bash
    python main.py
    ```
    This executes the entire pipeline: data fetching/checking, processing, EDA, modeling, and report generation (output to `final_results.json` and console summary).

### Interactive Research

1.  Open the `ethereum_project` folder in an IDE supporting interactive Python (VS Code, Cursor, PyCharm, Jupyter).
2.  Ensure the IDE's Python interpreter is set to the project's virtual environment (`.venv/bin/python`).
3.  Open `research.py`. This file uses `#%%` cell markers for interactive execution.
    *   The first cell loads data (run `main.py` once first to generate `daily_clean.parquet` and `monthly_clean.parquet`).
    *   Subsequent cells provide examples for plotting and analysis.

## Testing

Tests are run using `pytest`. Ensure development dependencies are installed.
```bash
# Run all tests
pytest

# Run tests with coverage report (as in CI)
pytest --cov=src --cov-report=xml
# HTML report will be in htmlcov/
```

## Running with Docker

The project includes a `Dockerfile` for building and running in an isolated container environment.

1.  **Build the Docker Image:**
    ```bash
    docker build -t ethereum_project .
    ```

2.  **Run Tests in the Container:**
    ```bash
    docker run --rm ethereum_project pytest -q
    ```

3.  **Run the Main Application in the Container:**
    ```bash
    # Using the dummy RAPIDAPI_KEY set in the Dockerfile (may not fetch live data)
    docker run --rm ethereum_project

    # To use a real API key for live data fetching:
    docker run --rm -e RAPIDAPI_KEY="your_actual_rapidapi_key" ethereum_project
    ```
    The Docker image is based on `python:3.12-slim`.

## Configuration File Details

For detailed contents of project configuration files (e.g., `.gitignore`, `.pre-commit-config.yaml`, `mypy.ini`, GitHub Actions workflows), please refer to **`PROJECT_CONFIG_DETAILS.md`**. This document is specifically curated to provide comprehensive context for LLMs.

## Key Dependencies (from `requirements-lock.txt`)

*   `pandas` (e.g., 2.2.3)
*   `numpy` (e.g., 1.26.4)
*   `statsmodels` (e.g., 0.14.1)
*   `linearmodels` (e.g., 6.1)
*   `scikit-learn` (e.g., 1.5.2)
*   `matplotlib` (e.g., 3.10.1)
*   `seaborn` (e.g., 0.13.2)
*   `requests` (e.g., 2.32.3)
*   `pydantic` (e.g., 1.10.22)
*   `pyarrow` (e.g., 20.0.0)
*   (See `requirements-lock.txt` for the full list and exact versions.)

## Notes on Python Versions & Dependencies

*   **Current Local Development:** Python 3.11 (see `.python-version`).
*   **Current Docker Environment:** Python 3.12 (see `Dockerfile`).
*   **Locked Dependencies (`requirements-lock.txt`):** Generated using `pip-compile` (header indicates Python 3.13 was used for compilation, likely for forward compatibility checks). These are the versions used for stable runs.
*   **Development Dependencies (`requirements-dev.txt`):** May specify broader ranges or newer versions for tools and future compatibility testing (e.g., targeting Python 3.13+). Compatibility with the main `src/` code is not guaranteed with these bleeding-edge versions without code updates.

## License

This project is licensed under the terms of the [MIT License](LICENSE). (Assuming MIT, please verify `LICENSE` file content).

## Collaboration & CI (For Human Contributors)

*   **Branching**: Work on feature branches (`feature/<topic>`), submit Pull Requests to `main`.
*   **CI**: GitHub Actions run linters, type checkers, and tests on Python 3.10-3.12 (see `.github/workflows/`).
*   **Pre-commit**: Use `pre-commit run --all-files` locally before pushing.
(Details of CI workflows are in `PROJECT_CONFIG_DETAILS.md`) 