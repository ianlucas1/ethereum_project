# Data Flow Diagram

This diagram details the sequence of operations and data transformations within the `ethereum_project` pipeline when `src/main.py` is executed.

```mermaid
sequenceDiagram
    actor User
    participant main_py as Main Script (src/main.py)
    participant data_fetch as Data Fetching (src/data_fetching.py)
    participant utils_api as API Helpers (src/utils/api_helpers.py)
    participant utils_cache as Cache (src/utils/cache.py)
    participant data_proc as Data Processing (src/data_processing.py)
    participant eda_mod as EDA (src/eda.py)
    participant model_mods as Modeling (src/ols_models.py, src/ts_models.py)
    participant diag_mod as Diagnostics (src/diagnostics.py)
    participant val_mod as Validation (src/validation.py)
    participant report_mod as Reporting (src/reporting.py)
    participant FS as Filesystem (data/ directory)

    User->>main_py: Execute `python src/main.py`
    main_py->>data_proc: Call ensure_raw_data_exists()
    data_proc->>data_fetch: Fetch raw data (if not exists or stale)
    data_fetch->>utils_cache: Check/Use Disk Cache
    alt Data not in cache or cache needs refresh
        data_fetch->>utils_api: Request data from External APIs
        utils_api-->>data_fetch: Raw Data Response
        data_fetch->>utils_cache: Store Raw Data to Disk Cache
        data_fetch->>FS: Optionally save raw data copies (e.g. Parquet)
    end
    utils_cache-->>data_fetch: Raw DataFrames
    data_fetch-->>data_proc: Raw DataFrames

    main_py->>data_proc: Call process_all_data()
    data_proc->>FS: Load Raw Data (if needed)
    data_proc->>data_proc: Internal: Merge sources, Clean, Transform Features, Resample (Daily/Monthly)
    data_proc->>FS: Save daily_clean.parquet
    data_proc->>FS: Save monthly_clean.parquet
    data_proc-->>main_py: daily_cleaned_df, monthly_cleaned_df

    main_py->>eda_mod: Call winsorize_data(monthly_cleaned_df)
    eda_mod-->>main_py: monthly_winsorized_df
    main_py->>eda_mod: Call run_stationarity_tests(monthly_winsorized_df)
    eda_mod-->>main_py: stationarity_results_dict

    main_py->>model_mods: Call run_ols_benchmarks(daily_cleaned_df, monthly_for_ols_df)
    model_mods-->>main_py: ols_results_dict
    opt OLS Extended Model Exists
        main_py->>diag_mod: Call run_residual_diagnostics(ols_extended_model_fit)
        diag_mod-->>main_py: ols_diagnostics_dict
        main_py->>diag_mod: Call run_structural_break_tests(ols_extended_model_fit)
        diag_mod-->>main_py: ols_structural_breaks_dict
    end

    main_py->>model_mods: Call run_vecm_analysis(model_input_df)
    model_mods-->>main_py: vecm_results_dict
    main_py->>model_mods: Call run_ardl_analysis(model_input_df)
    model_mods-->>main_py: ardl_results_dict

    main_py->>val_mod: Call run_oos_validation(monthly_winsorized_df)
    val_mod-->>main_py: oos_results_dict (includes OOS predictions_df)

    main_py->>report_mod: Call generate_summary(all_accumulated_results)
    report_mod-->>main_py: final_summary_dict, interpretation_text_str
    main_py->>FS: Save final_results.json
    main_py->>User: Print interpretation_text_str to console
```
This sequence illustrates the interaction between different modules, data caching, file system operations for storing intermediate and final results, and the eventual output to the user. 