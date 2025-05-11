# Ethereum Econometric Valuation Analysis

[![Python CI](https://github.com/ianlucas1/ethereum_project/actions/workflows/python-ci.yml/badge.svg)](https://github.com/ianlucas1/ethereum_project/actions/workflows/python-ci.yml)
[![CodeQL](https://github.com/ianlucas1/ethereum_project/actions/workflows/codeql.yml/badge.svg)](https://github.com/ianlucas1/ethereum_project/actions/workflows/codeql.yml)
[![Nightly Audit](https://github.com/ianlucas1/ethereum_project/actions/workflows/nightly_audit.yml/badge.svg)](https://github.com/ianlucas1/ethereum_project/actions/workflows/nightly_audit.yml)
[![Security Scan](https://github.com/ianlucas1/ethereum_project/actions/workflows/static-security.yml/badge.svg)](https://github.com/ianlucas1/ethereum_project/actions/workflows/static-security.yml)

## Overview

This project conducts an econometric analysis of Ethereum (ETH) valuation, primarily exploring its relationship with network activity metrics, drawing inspiration from Metcalfe's Law. It aims to identify key drivers of ETH's value using various statistical models. The project fetches, processes, and analyzes on-chain and market data for Ethereum and benchmark assets like the NASDAQ index.

The primary execution script is `main.py` (or `src/main.py`), which runs the complete end-to-end analysis pipeline. For interactive data exploration, model development, and visualization, `research.py` provides a suitable environment.

**For comprehensive technical documentation, please refer to the [MkDocs site](docs/index.md) (build locally with `mkdocs serve` or view deployed version).**

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

## Quick-Start

### Option 1: Using Docker (Recommended for isolated execution)

1.  **Ensure Docker is installed and running.**
2.  **Clone the repository:**
    ```bash
    git clone https://github.com/ianlucas1/ethereum_project.git
    cd ethereum_project
    ```
3.  **Build the Docker image:**
    ```bash
    docker build -t ethereum_project .
    ```
4.  **Run the analysis (replace with your actual API key):**
    ```bash
    docker run --rm -e RAPIDAPI_KEY="YOUR_RAPIDAPI_KEY" ethereum_project
    ```
    Output files (like `final_results.json` and plots) will be created inside the container. To access them, you can mount a local directory:
    ```bash
    mkdir -p ./data_output ./snapshots_output
    docker run --rm \
      -e RAPIDAPI_KEY="YOUR_RAPIDAPI_KEY" \
      -v "$(pwd)/data_output:/app/data" \
      -v "$(pwd)/snapshots_output:/app/snapshots" \
      ethereum_project
    ```
    Check `data_output/final_results.json` after the run.

### Option 2: Local Virtual Environment (for development or direct script execution)

1.  **Prerequisites:** Python 3.12, Git.
2.  **Clone the repository and navigate into it** (as above).
3.  **Set up and activate a virtual environment:** (See `docs/how-to/install.md` for details)
    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate # On macOS/Linux
    # .\\\.venv\\Scripts\\activate # On Windows
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements-lock.txt
    ```
5.  **Set up environment variables:** Create a `.env` file in the root directory with your `RAPIDAPI_KEY`. (See `docs/reference/config.md`)
    ```dotenv
    RAPIDAPI_KEY=YOUR_RAPIDAPI_KEY
    ```
6.  **Run the main pipeline:**
    ```bash
    python src/main.py
    ```

## Technology Stack

*   **Language**: Python
*   **Core Libraries**:
    *   `pandas` (for data manipulation)
    *   `numpy` (for numerical operations)
    *   `statsmodels` (for statistical models, e.g., OLS, ARDL, VECM diagnostics)
    *   `scikit-learn` (for utility functions like preprocessing)
    *   `matplotlib` (for data visualization)
    *   `requests` (for API communication)
    *   `pydantic` (with pydantic-settings for configuration management)
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
├── scripts/                     # Utility scripts (e.g., qa_audit.py for dev checks)
├── src/                         # Core source code
│   ├── utils/                   # Utility modules (caching, API helpers, file I/O)
│   ├── __init__.py
│   ├── config.py                # Project configuration (loads .env)
│   ├── data_fetching.py         # Data retrieval logic from APIs
│   ├── data_processing.py       # Data cleaning, transformation, feature engineering
│   ├── diagnostics.py           # Model diagnostic tests
│   ├── eda.py                   # Exploratory Data Analysis functions
│   ├── main.py                  # Symlink or copy of src/main.py (entry point)
│   ├── ols_models.py            # OLS regression models
│   ├── reporting.py             # Results summarization and output generation
│   ├── ts_models.py             # Time series models (VECM, ARDL)
│   └── validation.py            # Out-of-sample validation logic
├── tests/                       # Automated tests
├── .dockerignore                # Specifies files to exclude from Docker builds
├── .gitignore                   # Specifies intentionally untracked files for Git
├── .pre-commit-config.yaml      # Configuration for pre-commit hooks (linters, formatters)
├── .python-version              # Specifies the project's Python version (e.g., for pyenv)
├── Dockerfile                   # Defines the Docker image for the project
├── LICENSE                      # Project license information
├── mypy.ini                     # Configuration for mypy static type checker
├── pip.conf                     # pip configuration (e.g., extra index URLs)
├── PROJECT_CONFIG_DETAILS.md    # Detailed content of config files for reference
├── README.md                    # This file
├── research.py                  # Script for interactive research and plotting
├── requirements-dev.txt         # Dependencies for development
└── requirements-lock.txt        # Pinned versions of all dependencies
```

## Modules (`src/` directory)

*   `config.py`: Manages project settings and API keys, primarily by loading them from an `.env` file.
*   `data_fetching.py`: Handles fetching raw data from external APIs (e.g., CoinMetrics, Yahoo Finance), including caching mechanisms.
*   `data_processing.py`: Cleans, transforms, merges, and resamples raw data into analysis-ready `daily_clean.parquet` and `monthly_clean.parquet` datasets.
*   `diagnostics.py`: Implements model diagnostic tests, such as residual analysis and structural break tests.
*   `eda.py`: Provides functions for exploratory data analysis, including data winsorization and stationarity tests (e.g., ADF).
*   `main.py`: The main entry point script for executing the full end-to-end analysis pipeline.
*   `ols_models.py`: Implements Ordinary Least Squares (OLS) benchmark models.
*   `reporting.py`: Generates summaries of analysis results, formats them into a structured dictionary, and handles JSON serialization.
*   `ts_models.py`: Implements time series models like Vector Error Correction Models (VECM) and Autoregressive Distributed Lag (ARDL) models.
*   `validation.py`: Handles out-of-sample model validation, particularly rolling window validation.
*   `utils/`: A sub-package containing various utility modules:
    *   `cache.py`: Caching utilities.
    *   `api_helpers.py`: Helper functions for interacting with external APIs.
    *   `file_io.py`: Utilities for file input/output.

## Setup and Installation

For detailed setup and installation instructions, please see `docs/how-to/install.md`.

## Usage

For running the full pipeline either locally or via Docker, refer to the [Quick-Start](#quick-start) section above or the [tutorial on your first run](docs/tutorials/01-first-run.md).

Open `research.py` in an IDE supporting interactive Python (like VS Code with Jupyter extension or a Jupyter Notebook environment). Ensure the IDE's Python interpreter is set to the project's virtual environment (`.venv`).

## Testing

Tests are run using `pytest`. Ensure development dependencies are installed.
```bash
pytest # Run all tests
pytest --cov=src --cov-report=xml # Run tests with coverage
```

## Running with Docker

Refer to the [Quick-Start](#quick-start) section for Docker commands.

## Configuration File Details

For a reference on environment variables and other configurations, see `docs/reference/config.md`.

## Key Dependencies (from `requirements-lock.txt`)

The project relies on several key libraries, with exact versions pinned in `requirements-lock.txt` for reproducibility. Core runtime dependencies include:

*   `pandas==2.2.2`
*   `numpy==1.26.4`
*   `statsmodels==0.14.2`
*   `scikit-learn==1.5.0`
*   `matplotlib==3.8.4`
*   `requests==2.32.3`
*   `pydantic==2.7.4` (and `pydantic-settings==2.2.1` for configuration)
*   `pyarrow==15.0.2`

Development and testing tools such as `pytest`, `ruff`, `mypy`, and `pre-commit` are also pinned. Please refer to `requirements-lock.txt` for the complete list of all direct and transitive dependencies.

## Notes on Python Versions & Dependencies

*   **Local Development:** Python 3.12 (specified in `.python-version`).
*   **Docker Environment:** Python 3.12 (specified in `Dockerfile`).
*   **CI Testing:** Primarily targets Python 3.12 across multiple operating systems.
*   **Locked Dependencies (`requirements-lock.txt`):** Generated using `pip-compile` with Python 3.12. These are the exact versions for reproducible runs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

For information on third-party licenses, please see the [NOTICE.md](NOTICE.md) file.

## Collaboration & CI (For Human Contributors)

Please refer to `CONTRIBUTING.md` for guidelines. Key points:
*   Work on feature branches and submit Pull Requests to `main`.
*   GitHub Actions automate CI checks (linting, testing, security scans).
*   Use `pre-commit` hooks locally before pushing.

For more details on the CI pipeline, see `docs/ci/pipeline.md`.