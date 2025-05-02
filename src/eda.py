# src/eda.py

import logging
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from scipy.stats import jarque_bera # Keep JB here if used in EDA/diagnostics
import warnings # <-- Added import
from statsmodels.tools.sm_exceptions import InterpolationWarning # <-- Added import

# --- Data Preprocessing Functions ---

def winsorize_data(df: pd.DataFrame, cols_to_cap: list[str], quantile: float = 0.995) -> pd.DataFrame:
    """
    Winsorizes specified columns of a DataFrame at a given quantile.
    Adds an 'outlier_dummy' column flagging rows where capping occurred.
    Recomputes log_active and log_gas if their inputs were capped.

    Args:
        df: Input DataFrame.
        cols_to_cap: List of column names to winsorize.
        quantile: The quantile (e.g., 0.995) at which to cap.

    Returns:
        A new DataFrame with winsorized data and outlier dummy.
    """
    logging.info(f"Starting winsorization for columns: {cols_to_cap} at quantile {quantile}")
    df_out = df.copy()
    outlier_mask = np.zeros(len(df_out), dtype=bool)

    # Check if columns exist before attempting to winsorize
    valid_cols_to_cap = [col for col in cols_to_cap if col in df_out.columns]
    if len(valid_cols_to_cap) < len(cols_to_cap):
        missing = set(cols_to_cap) - set(valid_cols_to_cap)
        logging.warning(f"Columns not found for winsorizing, skipping: {missing}")

    if not valid_cols_to_cap:
        logging.warning("No valid columns provided for winsorizing.")
        df_out["outlier_dummy"] = outlier_mask.astype(int)
        return df_out

    for col in valid_cols_to_cap:
        if pd.api.types.is_numeric_dtype(df_out[col]):
            cap_val = df_out[col].quantile(quantile)
            # Ensure cap_val is not NaN before comparison
            if pd.notna(cap_val):
                mask = df_out[col] > cap_val
                outlier_mask |= mask            # accumulate spikes across all capped cols
                df_out.loc[mask, col] = cap_val     # winsorise
                logging.info(f"  Capped {col} at {cap_val:,.2f}. {mask.sum()} values affected.")
            else:
                logging.warning(f"Could not calculate quantile {quantile} for column '{col}', skipping winsorization.")
        else:
            logging.warning(f"Column '{col}' is not numeric, skipping winsorization.")

    df_out["outlier_dummy"] = outlier_mask.astype(int)
    total_spikes = outlier_mask.sum()
    logging.info(f"Winsorizing complete. Total spike days flagged: {total_spikes}")

    # Re-compute dependent log variables if their inputs were changed
    # Need to check if the base columns exist before recalculating logs
    if "active_addr" in valid_cols_to_cap and "active_addr" in df_out.columns:
        if 'log_active' in df_out.columns:
             logging.info("Recomputing log_active after winsorizing active_addr.")
             with np.errstate(divide='ignore', invalid='ignore'):
                 df_out["log_active"] = np.log(df_out["active_addr"].replace(0, np.nan))
        else:
             logging.warning("Cannot recompute log_active: column not found.")

    # Determine the correct burn column name used previously
    burn_col_options = ["burn", "burn_native", "feetotntv", "feeburnntv"]
    burn_col_actual = next((c for c in valid_cols_to_cap if c.lower() in burn_col_options), None)

    if burn_col_actual and burn_col_actual in df_out.columns:
         if 'log_gas' in df_out.columns:
             logging.info(f"Recomputing log_gas after winsorizing {burn_col_actual}.")
             df_out["log_gas"] = np.log1p(df_out[burn_col_actual]) # log1p handles 0 correctly
         else:
              logging.warning("Cannot recompute log_gas: column not found.")

    # Replace inf/-inf that might result from log(0) if replace didn't catch it
    df_out.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df_out


# --- Diagnostic Functions ---

def run_stationarity_tests(df: pd.DataFrame, cols_to_test: list[str]) -> pd.DataFrame:
    """
    Performs ADF and KPSS stationarity tests on specified columns.

    Args:
        df: Input DataFrame.
        cols_to_test: List of column names to test.

    Returns:
        A DataFrame summarizing the test results.
    """
    logging.info(f"Running stationarity tests (ADF, KPSS) for: {cols_to_test}")
    results = []

    # Check if columns exist
    valid_cols_to_test = [col for col in cols_to_test if col in df.columns]
    if len(valid_cols_to_test) < len(cols_to_test):
        missing = set(cols_to_test) - set(valid_cols_to_test)
        logging.warning(f"Columns not found for stationarity tests, skipping: {missing}")

    if not valid_cols_to_test:
        logging.warning("No valid columns provided for stationarity tests.")
        return pd.DataFrame()

    # Nested helper functions for tests
    def adf_test(series):
        try:
            # Ensure series is float type for ADF
            stat, p, *_ = adfuller(series.astype(float), autolag="AIC")
            return stat, p
        except Exception as e:
            logging.error(f"ADF test failed for series {series.name}: {e}")
            return np.nan, np.nan

    def kpss_test(series):
        # KPSS test requires minimum observations, handle potential errors
        if len(series) < 10: # Arbitrary minimum, adjust if needed
             logging.warning(f"KPSS test skipped for {series.name}: insufficient observations ({len(series)})")
             return np.nan, np.nan
        try:
            # Suppress KPSS warnings about p-value interpolation
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=InterpolationWarning)
                # Ensure series is float type for KPSS
                kpss_result = kpss(series.astype(float), regression="c", nlags="auto")
                stat, p = kpss_result[0], kpss_result[1] # Get first two return values
            return stat, p
        except Exception as e:
            logging.error(f"KPSS test failed for series {series.name}: {e}")
            return np.nan, np.nan

    for col in valid_cols_to_test:
        # Use df here, not df_out
        if col in df.columns:
            s = df[col].dropna()
            if s.empty:
                logging.warning(f"Skipping stationarity tests for {col}: Series is empty after dropna.")
                adf_stat, adf_p = np.nan, np.nan
                kpss_stat, kpss_p = np.nan, np.nan
            else:
                adf_stat, adf_p = adf_test(s)
                kpss_stat, kpss_p = kpss_test(s)

            results.append({
                "series": col,
                "ADF stat": f"{adf_stat:+.2f}" if pd.notna(adf_stat) else "N/A",
                "ADF p":    f"{adf_p:.3f}" if pd.notna(adf_p) else "N/A",
                "KPSS stat":f"{kpss_stat:+.2f}" if pd.notna(kpss_stat) else "N/A",
                "KPSS p":   f"{kpss_p:.3f}" if pd.notna(kpss_p) else "N/A",
            })
        else:
             logging.warning(f"Column {col} not found in DataFrame for stationarity test.")


    stationarity_tbl = pd.DataFrame(results)
    logging.info("Stationarity tests complete.")
    print("\n--- Stationarity Test Results ---")
    try:
        from IPython.display import display
        display(stationarity_tbl)
    except ImportError:
        print(stationarity_tbl)
    print("---------------------------------\n")

    return stationarity_tbl

# Note: The original EDA plots/summaries from In[5] are not included here.
# They can be added as separate functions if needed for the final workflow.