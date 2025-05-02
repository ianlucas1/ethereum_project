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

## Collaboration & GitHub Workflow 🚀

| What | How |
|------|-----|
| **Default branch** | `main` (protected by ruleset) |
| **Branching** | Work on short-lived branches (`feature/<topic>`). **Never** push directly to `main`. |
| **Pull requests** | Required for every change; CI must pass; at least **1** approving review. |
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
*   `eda.py`: Provides functions for exploratory data analysis and preprocessing steps necessary before modeling, such as data winsorization and stationarity tests (e.g., ADF).
*   `modeling.py`: Implements the core econometric models, including Ordinary Least Squares (OLS) benchmarks, Vector Error Correction Models (VECM), Autoregressive Distributed Lag (ARDL) models, residual diagnostics, structural break tests, and out-of-sample validation.
*   `reporting.py`: Contains functions to generate summaries of the analysis results, format them into a structured dictionary, create interpretation text, and handle JSON serialization (including custom encoders for NumPy types).

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd ethereum_project
    ```

2.  **Create and Activate Virtual Environment:**
    It's highly recommended to use a virtual environment.
    ```bash
    # Create the virtual environment (using python3)
    python3 -m venv .venv

    # Activate the virtual environment
    # On macOS/Linux:
    source .venv/bin/activate
    # On Windows (Git Bash):
    # source .venv/Scripts/activate
    # On Windows (Command Prompt):
    # .venv\Scripts\activate.bat
    ```

3.  **Install Dependencies:**
    ```bash
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-lock.txt
    ```

4.  **Set Environment Variables:**
    The data fetching scripts require API keys. Set these as environment variables:
    *   `RAPIDAPI_KEY`: **Required** for fetching certain datasets via RapidAPI (ensure you have an account and key).
    *   `CM_API_KEY`: *Optional*. A CoinMetrics Pro API key can be used for fetching data directly. If not provided, the script might fall back to other sources or cached data where available.

    You can set these variables in your terminal session or use a `.env` file (make sure `.env` is added to `.gitignore`).
    Example (macOS/Linux):
    ```bash
    export RAPIDAPI_KEY="your_rapidapi_key_here"
    # export CM_API_KEY="your_coinmetrics_key_here" # Optional
    ```

    **Note on Specific Dependencies:**
    *   `statsmodels`: This project currently uses the development version (0.15.dev) directly from the GitHub main branch (`pip install git+https://github.com/statsmodels/statsmodels.git`). This is because the latest stable release (0.14.x) might have compatibility issues or lack necessary features. This requirement might be removed once `statsmodels` version 0.15 is officially released with pre-built wheels.
    *   `pyarrow`: Installation might pull pre-releases (nightlies) if necessary. This is facilitated by the inclusion of the Arrow nightlies package index (`https://pypi.fury.io/arrow-nightlies/`) in the `pip.conf` file, which allows `pip` to find these versions automatically.

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
2.  Ensure the IDE's Python interpreter is set to the project's virtual environment (`.venv`).
3.  Open `research.py`. This file contains `#%%` delimited cells.
4.  Run the cells sequentially using the IDE's "Run Cell" or similar commands.
    *   The first cell loads necessary libraries and the processed `daily_clean` and `monthly_clean` dataframes (assuming `main.py` has been run at least once to generate them).
    *   Subsequent cells contain example code (like plotting) that can be modified or extended for research purposes.

## Key Dependencies

The project relies on several key Python libraries:

*   `pandas`: Data manipulation and analysis.
*   `numpy`: Numerical operations.
*   `scipy`: Scientific and technical computing (used for stats functions).
*   `statsmodels`: Statistical models, econometric tests.
*   `linearmodels`: Panel data and IV regression models.
*   `scikit-learn`: Machine learning utilities (e.g., for potential preprocessing or validation metrics, though primary modeling is statsmodels/linearmodels).
*   `matplotlib`: Plotting library.
*   `seaborn`: High-level interface for drawing attractive statistical graphics.
*   `requests`: HTTP requests for data fetching.
*   `filelock`: Platform-independent file locking for caching.
*   `pyarrow`: Efficient backend for reading/writing Parquet files with pandas. 