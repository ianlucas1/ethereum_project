# Tutorial: Your First End-to-End Pipeline Run

This tutorial will guide you through running the entire `ethereum_project` analysis pipeline from start to finish. This includes data fetching, processing, modeling, and report generation.

## Prerequisites

1.  **Project Setup:** Ensure you have successfully completed all steps in the [Installation and Setup Guide](docs/how-to/install.md). This includes:
    *   Cloning the repository.
    *   Setting up Python 3.12 and a virtual environment (`.venv`).
    *   Installing all dependencies from `repo://requirements-lock.txt`.
    *   Creating a `.env` file in the project root with at least your `RAPIDAPI_KEY`.

2.  **Activated Virtual Environment:** Make sure your virtual environment is activated in your terminal session:
    ```bash
    source .venv/bin/activate  # On macOS/Linux
    # Or .\.venv\Scripts\activate on Windows
    ```

## Running the Pipeline

The main script to execute the full pipeline is `src/main.py`.

Navigate to the project root directory in your terminal and run the following command:

```bash
python src/main.py
```

Or, if you have the `main.py` symlink/copy in the root:
```bash
python main.py
```

## What to Expect During the Run

As the pipeline executes, you will see log messages printed to your console. These messages indicate the different stages of the analysis:

1.  **Starting Ethereum Valuation Analysis:** Initial message.
2.  **Checking/Fetching Raw Data:**
    *   The script will check if raw data exists in the cache or local files (e.g., in `data/raw/` or a cache directory defined by `repo://src/utils/cache.py`).
    *   If data is missing or stale, it will attempt to fetch it from external APIs. This step might take some time, especially on the first run or if the cache is empty. You'll see logs related to fetching specific datasets (e.g., Ethereum core metrics, NASDAQ).
    *   A plot of raw core data (`raw_core_data_plot.png`) might be generated in your `snapshots/` directory (or project root).
3.  **Running Data Processing:**
    *   Raw data is loaded, cleaned, merged, and transformed.
    *   Log features are engineered.
    *   Daily and monthly cleaned datasets (`daily_clean.parquet`, `monthly_clean.parquet`) are created and saved, typically in `data/processed/`.
4.  **Winsorising & Stationarity Tests:**
    *   Outliers in the monthly data are handled using winsorization.
    *   Stationarity tests (e.g., ADF, KPSS) are performed on key variables. Results of these tests will be logged.
5.  **Running Models:**
    *   **OLS Benchmarks:** Ordinary Least Squares models are run.
    *   **VECM Analysis:** Vector Error Correction Models are estimated.
    *   **ARDL Analysis:** Autoregressive Distributed Lag models are estimated.
    *   Log messages will indicate which model is being run and any key fitting information.
6.  **Model Diagnostics:**
    *   Residual diagnostics (e.g., for autocorrelation, heteroscedasticity) are performed on selected models (e.g., the extended OLS model).
    *   Structural break tests are conducted.
7.  **Out-of-Sample (OOS) Validation:**
    *   Models are validated on out-of-sample data using a rolling window approach.
8.  **Generating Report:**
    *   All analysis results are compiled.
    *   A summary interpretation of the findings will be printed to the console.
    *   A detailed JSON file containing all results will be saved.
9.  **Pipeline finished:** Final message.

## Expected Output

Upon successful completion:

1.  **Console Output:**
    *   You will see numerous log messages detailing the pipeline's progress.
    *   Towards the end, a textual summary and interpretation of the key findings from the analysis will be printed.
    ```
    ================================================================================
    ETH VALUATION ANALYSIS - KEY INTERPRETATIONS:
    ... [summary text] ...
    ================================================================================
    ```

2.  **`final_results.json`:**
    *   A JSON file named `final_results.json` will be created in your data directory (default: `data/final_results.json`).
    *   This file contains a structured dump of all results from the analysis, including data summaries, EDA test statistics, model coefficients, diagnostic p-values, OOS metrics, etc.

3.  **Other Potential Files:**
    *   `data/processed/daily_clean.parquet`
    *   `data/processed/monthly_clean.parquet`
    *   `snapshots/raw_core_data_plot.png` (or in project root)
    *   Cache files (typically in `data/cache/` or `snapshots/cache/` depending on `src/utils/cache.py` configuration).

## Troubleshooting

*   **`RAPIDAPI_KEY` errors:** Ensure your `.env` file is correctly set up with a valid `RAPIDAPI_KEY` and is in the project root.
*   **Missing Dependencies:** If you encounter `ModuleNotFoundError`, double-check that your virtual environment is activated and you've installed dependencies using `pip install -r requirements-lock.txt`.
*   **API Failures:** External APIs can sometimes be temporarily unavailable. The data fetching module has some retry logic, but persistent failures might require checking the API status or your network connection.
*   **File Path Issues:** If the script reports it cannot find or write files, check the permissions for your `data/` and `snapshots/` directories. The default `DATA_DIR` is `./data`.

Congratulations! You've successfully run the Ethereum econometric valuation analysis pipeline. You can now inspect the `final_results.json` for detailed model outputs or explore the generated plots. 