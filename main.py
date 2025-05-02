# main.py
import os # Make sure os is imported
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import json # Added for JSON output
import sys # Added for sys.exit on critical errors

# Import functions from our source modules
# Assuming Python can find the 'src' directory (it should if run from project root)
from src.utils import logging, DATA_DIR # Import logging configured in utils and DATA_DIR
# Import both processing functions now
from src.data_processing import process_all_data, ensure_raw_data_exists
from src.eda import winsorize_data, run_stationarity_tests
from src.modeling import (
    run_ols_benchmarks,
    run_residual_diagnostics,
    run_structural_break_tests,
    run_vecm_analysis,
    run_ardl_analysis,
    run_oos_validation
)
# Import reporting functions
from src.reporting import generate_summary, NpEncoder

# --- Configuration ---
# Define parameters here instead of hardcoding in functions
WINSORIZE_COLS = ["active_addr", "burn", "tx_count"] # Use 'burn' as defined in processing
WINSORIZE_QUANTILE = 0.995
STATIONARITY_COLS = ["log_marketcap", "log_active", "log_gas"] # After winsorizing
OLS_EXT_COLS = ["log_active", "log_nasdaq", "log_gas"]
BREAK_DATES = {
    "EIP1559": "2021-08-31",
    "Merge": "2022-09-30"
}
VECM_ENDOG_COLS = ["log_marketcap", "log_active"]
VECM_EXOG_COLS = ["log_nasdaq", "log_gas"]
ARDL_ENDOG_COL = "log_marketcap"
ARDL_EXOG_COLS = ["log_active", "log_nasdaq", "log_gas"]
OOS_WINDOW = 24
OOS_ENDOG_COL = "log_marketcap"
OOS_EXOG_COLS = ["log_active", "log_nasdaq", "log_gas"]
RESULTS_JSON_PATH = DATA_DIR.parent / "final_results.json" # Save JSON in project root


# --- Main Execution ---
def main():
    """Main function to run the Ethereum valuation analysis pipeline."""
    logging.info("--- Starting Ethereum Valuation Analysis ---")

    # --- ADDED BLOCK ---
    # 0. Ensure Raw Data Exists (Fetches if necessary)
    logging.info("--- Checking/Fetching Raw Data ---")
    # Set plot_diagnostics=False if you don't want the plot generated during fetch
    raw_data_ready = ensure_raw_data_exists(plot_diagnostics=True)
    if not raw_data_ready:
        logging.error("Could not ensure raw data is available. Exiting.")
        sys.exit(1) # Exit script if raw data cannot be obtained
    # --- END OF ADDED BLOCK ---

    # Dictionary to store all results
    analysis_results = {}

    # 1. Data Processing (Loads existing raw files, processes, saves clean files)
    logging.info("--- Running Data Processing ---")
    daily_clean, monthly_clean = process_all_data()

    if daily_clean.empty or monthly_clean.empty:
        logging.error("Data processing failed or returned empty dataframes. Exiting.")
        sys.exit(1) # Exit script if processing fails

    analysis_results['data_summary'] = {
        'daily_shape': daily_clean.shape,
        'monthly_shape': monthly_clean.shape,
        'monthly_start': monthly_clean.index.min(),
        'monthly_end': monthly_clean.index.max(),
    }
    # Keep copies for different stages
    monthly_clean_original = monthly_clean.copy() # Before any modifications by analysis steps
    monthly_clean_for_ols = monthly_clean.copy() # OLS benchmarks will modify this one

    # 2. Pre-Modeling EDA/Preprocessing (on Monthly Data for modeling)
    logging.info("--- Running Pre-Modeling Steps (Winsorize, Stationarity) ---")
    monthly_winsorized = winsorize_data(monthly_clean_original, WINSORIZE_COLS, WINSORIZE_QUANTILE)
    monthly_winsorized.replace([np.inf, -np.inf], np.nan, inplace=True) # Re-check NaNs

    analysis_results['stationarity'] = run_stationarity_tests(monthly_winsorized, STATIONARITY_COLS)

    # 3. Modeling & Diagnostics
    logging.info("--- Running Modeling ---")

    # Ensure the dataframe used for dynamic modeling doesn't have NaNs in key columns
    model_df = monthly_winsorized.dropna(subset=[ARDL_ENDOG_COL] + ARDL_EXOG_COLS).copy() # Use copy
    if model_df.empty:
         logging.error("DataFrame is empty after dropping NaNs before dynamic modeling. Exiting.")
         sys.exit(1) # Exit script if no data for dynamic models

    # OLS Benchmarks (uses non-winsorized data, modifies monthly_clean_for_ols)
    ols_results = run_ols_benchmarks(daily_clean, monthly_clean_for_ols)
    analysis_results['ols'] = ols_results

    # Diagnostics on Extended OLS
    ols_ext_fit_results = ols_results.get('monthly_extended', {})
    if ols_ext_fit_results.get("model_obj"):
        analysis_results['ols_diagnostics'] = run_residual_diagnostics(ols_ext_fit_results)
        analysis_results['ols_structural_breaks'] = run_structural_break_tests(ols_ext_fit_results, BREAK_DATES)
    else:
        logging.warning("Extended OLS model failed, skipping diagnostics and break tests.")
        analysis_results['ols_diagnostics'] = {"error": "Extended OLS failed."}
        analysis_results['ols_structural_breaks'] = {"error": "Extended OLS failed."}

    # VECM Analysis (using winsorized, NaN-dropped data)
    vecm_req_cols = VECM_ENDOG_COLS + (VECM_EXOG_COLS if VECM_EXOG_COLS else [])
    if all(col in model_df.columns for col in vecm_req_cols):
         analysis_results['vecm'] = run_vecm_analysis(model_df, VECM_ENDOG_COLS, VECM_EXOG_COLS)
    else:
         missing = set(vecm_req_cols) - set(model_df.columns)
         logging.warning(f"Skipping VECM: Missing required columns {missing} in modeling dataframe.")
         analysis_results['vecm'] = {"error": f"Missing columns: {missing}"}

    # ARDL Analysis (using winsorized, NaN-dropped data)
    ardl_req_cols = [ARDL_ENDOG_COL] + ARDL_EXOG_COLS
    if all(col in model_df.columns for col in ardl_req_cols):
        analysis_results['ardl'] = run_ardl_analysis(model_df, ARDL_ENDOG_COL, ARDL_EXOG_COLS)
    else:
         missing = set(ardl_req_cols) - set(model_df.columns)
         logging.warning(f"Skipping ARDL: Missing required columns {missing} in modeling dataframe.")
         analysis_results['ardl'] = {"error": f"Missing columns: {missing}"}

    # OOS Validation (using winsorized, NaN-dropped data for consistency)
    # Note: OOS function internally drops NaNs for its modeling columns
    oos_req_cols = [OOS_ENDOG_COL] + OOS_EXOG_COLS + ['price_usd', 'supply']
    # Check if columns exist in the base winsorized df before passing to OOS
    if all(col in monthly_winsorized.columns for col in oos_req_cols):
         # Pass the winsorized df, OOS function will handle NaN dropping internally for its specific needs
         oos_results = run_oos_validation(monthly_winsorized, OOS_ENDOG_COL, OOS_EXOG_COLS, window_size=OOS_WINDOW)
         analysis_results['oos'] = oos_results
         # Add OOS predictions back to the main modeling dataframe if successful
         if 'predictions_df' in oos_results:
              preds_df = oos_results['predictions_df']
              # Add to model_df (which is based on monthly_winsorized but NaN-dropped for dynamic models)
              model_df['predicted_price_oos'] = preds_df['predicted_price_oos'].reindex(model_df.index)
    else:
         missing = set(oos_req_cols) - set(monthly_winsorized.columns)
         logging.warning(f"Skipping OOS Validation: Missing required columns {missing} in monthly_winsorized dataframe.")
         analysis_results['oos'] = {"error": f"Missing columns: {missing}"}


    # 4. Reporting
    logging.info("--- Generating Report ---")
    # Pass the OLS-modified df for fair value, and the model_df (which might contain OOS preds)
    summary_output = generate_summary(analysis_results, monthly_clean_for_ols, model_df)
    final_results_dict = summary_output['final_dict']
    interpretation_text = summary_output['interpretation_text']

    # Print interpretation to console
    print("\n" + "="*80)
    print(interpretation_text)
    print("="*80 + "\n")

    # Save final results dictionary to JSON
    try:
        with open(RESULTS_JSON_PATH, 'w') as f:
            json.dump(final_results_dict, f, indent=4, cls=NpEncoder)
        logging.info(f"Final results dictionary saved to: {RESULTS_JSON_PATH}")
    except Exception as e:
        logging.error(f"Failed to save final results JSON: {e}", exc_info=True)


    logging.info("--- Script Finished ---")


if __name__ == "__main__":
    # Ensure API keys are loaded from environment variables if needed
    # Example: Check for RAPIDAPI_KEY (can add CM_API_KEY check too)
    if not os.getenv("RAPIDAPI_KEY"):
         # Making this an error and exiting, as fetching is required if data is missing
         logging.error("RAPIDAPI_KEY environment variable not set. This is required for data fetching.")
         sys.exit("Error: RAPIDAPI_KEY environment variable is required.")
         # Alternatively, warn and continue if cached data might exist:
         # logging.warning("RAPIDAPI_KEY environment variable not set. Data fetching might fail if cache is old/missing.")

    # Run the main analysis pipeline
    main()
