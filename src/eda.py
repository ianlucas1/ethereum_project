# src/eda.py

import logging
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from scipy.stats import jarque_bera # Keep JB here if used in EDA/diagnostics
import warnings # <-- Added import
from statsmodels.tools.sm_exceptions import InterpolationWarning # <-- Added import
from scipy.stats.mstats import winsorize
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

# --- Data Preprocessing Functions ---

def winsorize_data(df: pd.DataFrame, cols_to_cap: list[str], quantile: float = 0.995, window_mask: pd.Index | None = None) -> pd.DataFrame:
    """
    Caps specified columns in a DataFrame at the specified upper quantile.

    Args:
        df: Input DataFrame.
        cols_to_cap: List of column names to cap.
        quantile: The upper quantile to cap at (e.g., 0.99 for 99th percentile).
                  Only the upper tail is capped. Defaults to 0.995.
            window_mask: Optional index slice to calculate the quantile over. If None,
                         uses the full DataFrame. Defaults to None.

    Returns:
        DataFrame with specified columns capped.
    """
    df_out = df.copy()
    capped_cols = []

    for col in cols_to_cap:
        if col not in df_out.columns:
            logger.warning(f"Column '{col}' not found in DataFrame. Skipping capping.")
            continue

        if not pd.api.types.is_numeric_dtype(df_out[col]):
            logger.warning(f"Column '{col}' is not numeric. Skipping capping.")
            continue

        # Calculate the cap value based on the specified quantile
        data_for_quantile = df_out.loc[window_mask, col] if window_mask is not None else df_out[col]
        cap_val = data_for_quantile.quantile(quantile)

        # Identify all values exceeding the cap across the DataFrame
        mask_exceeding_cap = df_out[col] > cap_val

        if window_mask is not None:
            # If a window is specified, only apply capping *within* that window
            mask_to_cap = mask_exceeding_cap & window_mask # Intersect exceeding mask with window mask
            df_out.loc[mask_to_cap, col] = cap_val
            num_capped = mask_to_cap.sum()
            logger.info(f"Capped column '{col}' at {quantile*100:.1f}th percentile (value: {cap_val:.4f}) within window. {num_capped} values affected.")
        else:
            # If no window, apply capping to all values exceeding the cap (original behavior)
            df_out.loc[mask_exceeding_cap, col] = cap_val
            num_capped = mask_exceeding_cap.sum()
            logger.info(f"Capped column '{col}' at {quantile*100:.1f}th percentile (value: {cap_val:.4f}). {num_capped} values affected.")

        if num_capped > 0: # Only append if capping actually occurred
            capped_cols.append(col)

    if not capped_cols:
        logger.warning("No columns were capped.")

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