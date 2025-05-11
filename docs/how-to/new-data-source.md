# How-to: Add a New Data Source

This guide outlines the steps involved in adding a new data source to the `ethereum_project` pipeline. This typically involves fetching new data, processing it, and integrating it into the existing analysis workflow.

Let's assume you want to add a new daily time series, for example, "Ethereum Google Trends Index."

## Prerequisites

*   Familiarity with the project structure, especially `repo://src/data_fetching.py`, `repo://src/data_processing.py`, and `repo://src/config.py`.
*   Access to the new data source (e.g., an API endpoint, a downloadable CSV file).
*   Development environment set up as per `repo://docs/how-to/install.md`.

## Steps

### 1. Update Configuration (if necessary)

*   **API Key:** If the new data source requires an API key, add it to `repo://src/config.py` (within the `Settings` model) and provide its value in your `.env` file.
    ```python
    # In src/config.py
    class Settings(BaseSettings):
        # ... existing keys ...
        GOOGLE_TRENDS_API_KEY: str | None = None
        # ...
    ```
    ```dotenv
    # In .env
    GOOGLE_TRENDS_API_KEY="your_google_trends_key_if_needed"
    ```
*   **File Paths/URLs:** If fetching from a static URL or local file path, you might define it as a constant in `src/data_fetching.py` or manage it via `src/config.py`.

### 2. Implement Data Fetching Logic

In `repo://src/data_fetching.py`:

*   **Create a new fetch function:** Write a Python function to retrieve the data.
    *   Use `requests` or a specific client library for API calls.
    *   Utilize `repo://src/utils/api_helpers.py` for common API interaction patterns if applicable.
    *   Wrap your fetching function with the caching decorator from `repo://src/utils/cache.py` to avoid redundant calls.
    *   The function should return a pandas DataFrame with a DatetimeIndex (preferably named 'time').

    ```python
    # In src/data_fetching.py
    from .utils.cache import cache_data_to_parquet # Or your specific cache decorator

    @cache_data_to_parquet(cache_days=7, subdirectory="raw/google_trends")
    def fetch_google_trends_data(api_key: str | None) -> pd.DataFrame:
        # ... logic to call Google Trends API ...
        # Ensure data has a DatetimeIndex named 'time'
        # Example: df = pd.DataFrame({'google_trends_eth': [values]}, index=dates)
        # df.index.name = 'time'
        # return df
        pass # Replace with actual implementation
    ```
*   **Update `ensure_all_raw_data_fetched` (or similar orchestrator):** If you have a main function in `data_fetching.py` that calls all individual fetchers, add your new function call there.
    ```python
    # In src/data_fetching.py (example structure)
    def ensure_all_raw_data_fetched(config: Settings) -> None:
        # ... existing fetch calls ...
        fetch_google_trends_data(api_key=config.GOOGLE_TRENDS_API_KEY)
        logging.info("Google Trends data fetched/checked.")
    ```

### 3. Integrate into Data Processing

In `repo://src/data_processing.py`:

*   **Load the new raw data:** In `load_raw_data()` (or equivalent), add logic to load the parquet/CSV file saved by your new fetch function.
    ```python
    # In src/data_processing.py
    def load_raw_data() -> tuple[pd.DataFrame, ... , pd.DataFrame]: # Add new DF to tuple
        # ... existing loads ...
        try:
            google_trends_df = load_parquet(settings.DATA_DIR / "raw/google_trends/fetch_google_trends_data.parquet")
        except FileNotFoundError:
            logging.error("Google Trends raw data not found. Please ensure it's fetched.")
            # Decide on error handling: raise, return empty, etc.
            google_trends_df = pd.DataFrame()
        return core_df, fee_df, tx_df, nasdaq_df, google_trends_df # Updated return
    ```

*   **Update data merging:** In `merge_eth_data()` (or wherever primary merging occurs), join your new DataFrame with the main dataset. Ensure proper alignment on the DatetimeIndex.
    ```python
    # In src/data_processing.py
    def merge_eth_data(core_df: pd.DataFrame, ..., google_trends_df: pd.DataFrame) -> pd.DataFrame:
        # ... existing merges ...
        merged_df = pd.merge(merged_df, google_trends_df, on="time", how="left")
        return merged_df
    ```
    Handle potential NaNs introduced by the merge (e.g., `fillna(method='ffill')` or `fillna(0)` as appropriate for the new data).

*   **Feature Engineering:** If the new data requires transformations (e.g., log, differences, ratios), add these steps in `engineer_log_features()` or a new dedicated function.
    ```python
    # In src/data_processing.py
    def engineer_additional_features(df: pd.DataFrame) -> pd.DataFrame:
        df_eng = df.copy()
        if 'google_trends_eth' in df_eng.columns:
            df_eng['log_google_trends_eth'] = np.log1p(df_eng['google_trends_eth']) # Example
        return df_eng
    # Call this new function in process_all_data()
    ```

*   **Update `process_all_data()`:** Ensure the new data loading and feature engineering steps are incorporated into the main processing pipeline. The return signature of `load_raw_data` will change, so update its call.

### 4. Update Model Inputs & Constants (if applicable)

In `repo://src/main.py` (or relevant model configuration areas):

*   If the new data (or its engineered features) will be used as an explanatory variable in models:
    *   Add its column name to relevant lists like `OLS_EXT_COLS`, `VECM_EXOG_COLS`, `ARDL_EXOG_COLS`, `OOS_EXOG_COLS`.
*   If the new data needs pre-modeling EDA (like winsorization or stationarity testing):
    *   Add its column name to `WINSORIZE_COLS` or `STATIONARITY_COLS`.

### 5. Update Models (if applicable)

If the new data source is intended as a variable in your econometric models:

*   Review `repo://src/ols_models.py`, `repo://src/ts_models.py`.
*   The models often select columns dynamically based on the lists defined in `src/main.py`. If you've updated those lists, the models might pick up the new variable automatically.
*   However, you might need to adjust model specifications or interpretations based on the new variable's inclusion.

### 6. Add Tests

Crucially, add tests for your new functionality:

*   **`repo://tests/test_data_fetching.py`**:
    *   Test your new `fetch_google_trends_data()` function.
    *   Mock the external API call (`@patch`).
    *   Verify correct data parsing and DataFrame structure.
    *   Test caching behavior.
*   **`repo://tests/test_data_processing.py`**:
    *   Test the integration of the new data source into `load_raw_data`, `merge_eth_data`, and any new feature engineering functions.
    *   Use sample DataFrames (fixtures) for your new data.
    *   Verify correct merging, NaN handling, and feature calculations.
*   **Model Tests (Optional but Recommended):** If the new variable significantly changes model behavior, consider adding or adjusting tests in `repo://tests/test_ols_models.py` or `repo://tests/test_ts_models.py` to ensure models still run and produce plausible (though not necessarily "correct" in a unit test sense) outputs with the new variable.

### 7. Update Documentation

*   **This Guide:** If your process reveals new general steps, consider updating this guide.
*   **`repo://docs/reference/config.md`:** If you added new environment variables.
*   **Data Dictionary/Schema:** If you maintain a separate data dictionary, add the new variable(s) with descriptions. (This project doesn't seem to have one yet, but good practice for the future).
*   **Model Documentation:** If specific models are documented, update their variable lists.

### 8. Run Pre-commit Hooks and Test Suite

Before committing your changes:

```bash
pre-commit run --all-files
pytest
```

Ensure all checks and tests pass.

## Example Workflow Summary

1.  **Define Need:** Decide to add "Ethereum Google Trends Index."
2.  **API Key (if any):** Add `GOOGLE_TRENDS_API_KEY` to `config.py` and `.env`.
3.  **Fetch:** Implement `fetch_google_trends_data()` in `data_fetching.py` with caching.
4.  **Process:**
    *   Load in `load_raw_data()` in `data_processing.py`.
    *   Merge in `merge_eth_data()` in `data_processing.py`.
    *   Engineer `log_google_trends_eth` in `data_processing.py`.
5.  **Integrate:** Add `log_google_trends_eth` to `*_EXOG_COLS` lists in `main.py`.
6.  **Test:** Add unit tests for fetching and processing logic.
7.  **Document:** Update relevant documentation.

By following these steps, you can systematically integrate new data sources into the project, ensuring that data quality, processing, and analysis remain robust. 