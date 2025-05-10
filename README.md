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
    *   `scikit-learn` (for utility functions like preprocessing)
    *   `matplotlib` (for data visualization)
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
├── scripts/                     # Utility scripts (e.g., qa_audit.py for dev checks)
├── src/                         # Core source code
│   ├── utils/                   # Utility modules (caching, API helpers, file I/O)
│   ├── __init__.py
│   ├── config.py                # Project configuration (loads .env)
│   ├── data_fetching.py         # Data retrieval logic
│   ├── data_processing.py       # Data cleaning, transformation, feature engineering
│   ├── diagnostics.py           # Model diagnostic tests
│   ├── eda.py                   # Exploratory Data Analysis functions
│   ├── main.py                  # Main pipeline script (entry point for analysis)
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
├── LICENSE                      # Project license information
├── main.py                      # Main script to run the full analysis pipeline (symlink or copy of src/main.py)
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

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd ethereum_project
    ```

2.  **Ensure Correct Python Version:**
    *   The project is configured to use **Python 3.12** for local development, as specified in the `.python-version` file.
    *   The `Dockerfile` uses **Python 3.12-slim** for containerized execution. CI tests cover Python 3.12.
    *   Ensure you have Python 3.12 accessible for local work.

3.  **Create and Activate Virtual Environment (using Python 3.12):**
    Since `pyenv` is configured and the `.python-version` file specifies Python 3.12, the `python` command within this project directory will automatically point to your pyenv-managed Python 3.12 installation.
    ```bash
    python -m venv .venv # pyenv uses Python 3.12 due to .python-version
    source .venv/bin/activate # On macOS/Linux
    # .\.venv\Scripts\activate # On Windows PowerShell
    ```
    Ensure `.venv/` is in your `.gitignore`.

4.  **Install Dependencies:**
    Install the exact dependencies from the lock file:
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
    Create a `.env` file in the project root for API keys.
    Example `.env` content:
    ```dotenv
    RAPIDAPI_KEY=your_rapidapi_key_here
    CM_API_KEY=your_coinmetrics_key_here # Optional
    ETHERSCAN_API_KEY=your_etherscan_key_here # Optional (currently not used by the core pipeline)
    ```
    Ensure `.env` is listed in your `.gitignore` file.

## Usage

### Full Pipeline Execution

1.  Activate your virtual environment.
2.  Ensure required environment variables (at least `RAPIDAPI_KEY`) are set.
3.  Run `main.py` from the project root:
    ```bash
    python main.py
    ```
    This executes the entire pipeline and outputs results to `final_results.json` (which is gitignored) and a console summary.

### Interactive Research

1.  Open the project in an IDE supporting interactive Python.
2.  Ensure the IDE's Python interpreter is set to the project's virtual environment.
3.  Open `research.py` for interactive data exploration and model development.

## Testing

Tests are run using `pytest`. Ensure development dependencies are installed.
```bash
pytest # Run all tests
pytest --cov=src --cov-report=xml # Run tests with coverage
```

## Running with Docker

1.  **Build the Docker Image:**
    ```bash
    docker build -t ethereum_project .
    ```
2.  **Run the Main Application in the Container:**
    ```bash
    # Using the dummy RAPIDAPI_KEY set in the Dockerfile
    docker run --rm ethereum_project
    # To use a real API key:
    # docker run --rm -e RAPIDAPI_KEY="your_actual_rapidapi_key" ethereum_project
    ```

## Configuration File Details

For detailed contents of project configuration files (e.g., `.gitignore`, `.pre-commit-config.yaml`, `mypy.ini`, GitHub Actions workflows), please refer to **`PROJECT_CONFIG_DETAILS.md`**.

## Key Dependencies (from `requirements-lock.txt`)

The project relies on several key libraries, with exact versions pinned in `requirements-lock.txt` for reproducibility. Core runtime dependencies include:

*   `pandas==2.2.2`
*   `numpy==1.26.4`
*   `statsmodels==0.14.2`
*   `scikit-learn==1.5.0`
*   `matplotlib==3.8.4`
*   `requests==2.32.3`
*   `pydantic==1.10.14`
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

*   **Branching**: Work on feature branches, submit Pull Requests to `main`.
*   **CI**: GitHub Actions run linters, type checkers, and tests, primarily targeting Python 3.12 across multiple operating systems (see `.github/workflows/`).
*   **Pre-commit**: Use `pre-commit run --all-files` locally before pushing.
