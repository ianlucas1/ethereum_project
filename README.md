# Ethereum Econometric Valuation Analysis

## Overview

This project performs an econometric analysis of Ethereum (ETH) valuation, primarily exploring concepts related to Metcalfe's Law and network effects. It utilizes Python along with libraries such as `pandas` for data manipulation, `statsmodels` and `linearmodels` for econometric modeling, and `matplotlib`/`seaborn` for visualization.

The core analysis involves:
*   Fetching relevant on-chain and market data for Ethereum and benchmark assets (like NASDAQ).
*   Processing and cleaning the raw data into daily and monthly frequencies.
*   Performing exploratory data analysis (EDA), including outlier treatment and stationarity testing.
*   Building and evaluating various econometric models (OLS, VECM, ARDL) to understand the drivers of ETH's value.
*   Conducting out-of-sample validation.
*   Generating a summary report and saving structured results.

The project is structured to support both a full pipeline execution via `main.py` and interactive research/exploration using `research.py`.

## Collaboration & GitHub Workflow

| What | How |
|------|-----|
| **Default branch** | `main` (protected by ruleset) |
| **Branching** | Work on short-lived branches (`feature/<topic>`). **Never** push directly to `main`. |
| **Pull requests** | Required for every change; CI must pass |
| **Required check** | `Python CI` (runs unit tests & lint on Py 3.10 → 3.12). |
| **Merge methods** | Merge, Squash, or Rebase (choose what makes sense). |
| **Force pushes** | Disabled on `main`; allowed on your own branches with `--force-with-lease`. |
| **Dependencies** | Locked in `requirements-lock.txt`; update via `pip-compile` + PR. |
| **Local dev** | `python -m venv .venv && pip install -r requirements-lock.txt && pytest -q`. |
| **LLM etiquette** | Keep diffs minimal, commit messages clear (`feat:`, `fix:`, `docs:`), cite tools/sources. |

> **Tip**  Run `pre-commit run --all-files` before pushing to catch lint/format issues locally.

## Repository Structure

```
ethereum_project/
├── .venv/                       # Python virtual environment (created by user)
├── data/                        # Data files (raw fetched, processed clean)
│   ├── cm_{asset}_{metric}.parquet  # Raw CoinMetrics data examples
│   ├── eth_core.parquet         # Raw core ETH data
│   ├── eth_fee.parquet          # Raw ETH fee data
│   ├── eth_price_yf.parquet     # Raw ETH price from Yahoo Finance
│   ├── eth_tx.parquet           # Raw ETH transaction data
│   ├── nasdaq_ndx.parquet       # Raw NASDAQ index data
│   ├── daily_clean.parquet      # Processed daily data
│   └── monthly_clean.parquet    # Processed monthly data
├── src/                         # Source code modules
│   ├── __init__.py
│   ├── utils.py                 # Utilities (logging, constants, file paths)
│   ├── data_fetching.py         # Functions for fetching data from APIs
│   ├── data_processing.py       # Functions for cleaning and structuring data
│   ├── eda.py                   # Functions for EDA (winsorizing, stationarity)
│   ├── modeling.py              # Functions for econometric modeling (OLS, VECM, etc.)
│   └── reporting.py             # Functions for generating results summaries
├── .gitignore                   # Git ignore file
├── final_results.json           # Output JSON containing analysis results
├── main.py                      # Main script to run the full analysis pipeline
├── raw_core_data_plot.png       # Diagnostic plot generated during data fetching
├── README.md                    # This file
├── research.py                  # Script for interactive research and plotting (`#%%` cells)
└── requirements.txt             # Python package dependencies
```

## Modules (`src/` directory)

*   `utils.py`: Contains shared utility functions, constants (like `DATA_DIR`), and logging configuration used across the project.
*   `data_fetching.py`: Handles fetching raw data from external sources (e.g., CoinMetrics API, Yahoo Finance). Includes caching mechanisms to avoid redundant downloads.
*   `data_processing.py`: Responsible for cleaning, transforming, merging, and resampling the raw data into the `daily_clean.parquet` and `monthly_clean.parquet` datasets used for analysis.
*   `eda.py`: Provides functions for exploratory data analysis and preprocessing steps necessary before modeling. This includes *leak-free* data winsorization (calculating quantiles based only on the relevant training window to prevent lookahead bias) and stationarity tests (e.g., ADF).
*   `modeling.py`: Implements the core econometric models, including Ordinary Least Squares (OLS) benchmarks, Vector Error Correction Models (VECM), Autoregressive Distributed Lag (ARDL) models, residual diagnostics, structural break tests, and out-of-sample validation.
*   `validation.py`: Handles out-of-sample model validation, specifically implementing rolling window validation. Preprocessing steps like winsorization are applied *within* each training window iteration to prevent lookahead bias / data leakage.
*   `reporting.py`: Contains functions to generate summaries of the analysis results, format them into a structured dictionary, create interpretation text, and handle JSON serialization (including custom encoders for NumPy types).

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd ethereum_project
    ```

2.  **Ensure Correct Python Version:**
    *   This project is currently **verified to work with Python 3.12**. The dependencies in `requirements-lock.txt` were generated and tested in this environment.
    *   Make sure you have Python 3.12 installed and accessible (e.g., via `pyenv`, Homebrew, or direct download). You can check with `python3.12 --version`.

3.  **Create and Activate Virtual Environment (using Python 3.12):**
    It's highly recommended to use a virtual environment.
    ```bash
    # Create the virtual environment using python3.12
    python3.12 -m venv .venv

    # Activate the virtual environment
    # On macOS/Linux:
    source .venv/bin/activate
    # On Windows (Git Bash):
    # source .venv/Scripts/activate
    # On Windows (Command Prompt):
    # .venv\Scripts\activate.bat
    ```

4.  **Install Locked Dependencies:**
    Install the exact dependencies that the project was last verified with:
    ```bash
    pip install -r requirements-lock.txt
    ```

5.  **Set Environment Variables (using `.env` file):**
    The configuration (`src/config.py`) automatically loads API keys and other settings from a `.env` file in the project root directory. Create this file if it doesn't exist.

    *   **Create/Edit `.env` file:** In the project root, create or edit a file named `.env`.
    *   **Add Keys:** Add your keys to the file like this:
        ```dotenv
        # .env file content
        RAPIDAPI_KEY=your_rapidapi_key_here
        CM_API_KEY=your_coinmetrics_key_here # Optional - leave blank or comment out if not using Pro
        ETHERSCAN_API_KEY=your_etherscan_key_here # Optional - add if needed
        ```
    *   **Ensure `.gitignore**:** Double-check that your `.gitignore` file contains a line with just `.env` to prevent accidentally committing your keys.

    *(Alternatively, you can still set these as system environment variables, which will override the `.env` file if both are present, but using the `.env` file is recommended for managing project-specific keys.)*

## Usage

### Full Pipeline Execution

To run the entire analysis pipeline from data fetching/checking to final report generation:

1.  Ensure your virtual environment is activated.
2.  Ensure the required environment variables (at least `RAPIDAPI_KEY`) are set.
3.  Run `main.py` from the project root directory:
    ```bash
    python main.py
    ```

This script will:
*   Check for/fetch raw data (saving to `data/`).
*   Process data, saving `data/daily_clean.parquet` and `data/monthly_clean.parquet`.
*   Perform EDA and modeling steps.
*   Save the analysis results to `final_results.json`.
*   Print a summary interpretation to the console.
*   Potentially generate `raw_core_data_plot.png` during the initial data check.

### Interactive Research

For exploring data, visualizing results, or developing specific analysis components interactively:

1.  Open the `ethereum_project` folder in an IDE that supports interactive Python execution (like VS Code with the Python extension, Cursor, PyCharm, or Jupyter environments).
2.  Ensure the IDE's Python interpreter is set to the project's virtual environment (`.venv` - which should be Python 3.12).
3.  Open `research.py`. This file contains `#%%` delimited cells.
4.  Run the cells sequentially using the IDE's "Run Cell" or similar commands.
    *   The first cell loads necessary libraries and the processed `daily_clean` and `monthly_clean` dataframes (assuming `main.py` has been run at least once to generate them).
    *   Subsequent cells contain example code (like plotting) that can be modified or extended for research purposes.

## Notes on Dependencies and Python Versions

*   **Current Setup (Python 3.12):** The project currently runs reliably using **Python 3.12** and the specific package versions pinned in `requirements-lock.txt`. This includes `numpy==1.26.4` and `statsmodels==0.14.1`. This configuration was established to resolve compatibility issues encountered with newer versions.
*   **Target Setup (Python 3.13+, Future):** The `requirements-dev.txt` file specifies broader version ranges (e.g., `numpy>=2.1`, `statsmodels@git+...`) targeting **Python 3.13+** and newer library features (like the statsmodels development version). **This target setup is NOT currently guaranteed to work.** Future work is required to update the code in `src/` to be compatible with these newer dependencies (addressing potential API changes or runtime issues) and then regenerate `requirements-lock.txt` based on `requirements-dev.txt` in the newer Python environment.
*   **`pyarrow`:** Installation might pull pre-releases (nightlies) if necessary for compatibility, especially with newer Python versions. This was previously facilitated by an explicit index URL but may now rely on `--pre` flags or package availability.

## Key Dependencies (Current Working Set)

The project relies on several key Python libraries (versions as per `requirements-lock.txt`):

*   `pandas`: Data manipulation and analysis (e.g., 2.2.3).
*   `numpy`: Numerical operations (e.g., 1.26.4).
*   `scipy`: Scientific and technical computing (e.g., 1.15.2).
*   `statsmodels`: Statistical models, econometric tests (e.g., 0.14.1).
*   `linearmodels`: Panel data and IV regression models (e.g., 6.1).
*   `scikit-learn`: Machine learning utilities (e.g., 1.5.2).
*   `matplotlib`: Plotting library.
*   `seaborn`: High-level interface for drawing attractive statistical graphics.
*   `requests`: HTTP requests for data fetching.
*   `filelock`: Platform-independent file locking for caching.
*   `pyarrow`: Efficient backend for reading/writing Parquet files with pandas.
*   `pydantic`: Data validation and settings management (e.g., 1.10.22).

## 🚢 Running with Docker

The repository ships with a lightweight image definition (`Dockerfile`) so you can build
and test the project in an isolated container:

```bash
# build the image
docker build -t ethereum_project .

# run the tests inside the image
docker run --rm ethereum_project pytest -q

# run the main script (override the placeholder key if you need live API calls)
docker run --rm -e RAPIDAPI_KEY=your_real_key ethereum_project
```

> The image is based on **python 3.12-slim**, installs dependencies from
> `requirements-lock.txt`, and sets a dummy `RAPIDAPI_KEY` so tests pass without secrets. 