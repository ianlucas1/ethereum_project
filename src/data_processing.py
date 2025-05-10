"""Processes raw data into cleaned daily and monthly datasets.

Handles:
- Ensuring raw data files exist (fetching if necessary).
- Loading raw data (ETH core, fees, transactions, NASDAQ).
- Merging ETH datasets.
- Aligning and joining NASDAQ data.
- Engineering log-transformed features.
- Creating cleaned daily and monthly DataFrames.
- Saving processed DataFrames to parquet files.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING  # Added Any import

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Import settings, helpers from utils and data_fetching
from src.config import settings
from .data_fetching import cm_fetch, fetch_eth_price_rapidapi, fetch_nasdaq
from .utils import load_parquet

if TYPE_CHECKING:
    from matplotlib.figure import Figure


# --- Raw Data Creation ---


def _plot_core_data(df: pd.DataFrame, filename: str) -> None:
    """Helper to plot raw core data, saving with the specified filename.

    Args:
        df (pd.DataFrame): DataFrame containing 'price_usd', 'active_addr', 'supply'.
        filename (str): The filename (relative to project root) to save the plot.
    """
    logging.info("Plotting raw core data diagnostics...")
    try:
        fig: Figure
        # Corrected type hint for numpy array of Axes objects
        axes: np.ndarray
        fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
        # Save plot in project root using settings for consistency
        plot_path = settings.DATA_DIR / filename

        # Add checks for empty data before plotting
        if "price_usd" in df.columns and not df["price_usd"].dropna().empty:
            axes[0].plot(df.index, df["price_usd"])
            axes[0].set_yscale("log")
            axes[0].set_title("ETH Price (USD)")
        else:
            axes[0].set_title("ETH Price (USD) - No Data")

        if "active_addr" in df.columns and not df["active_addr"].dropna().empty:
            axes[1].plot(df.index, df["active_addr"])
            axes[1].set_title("Active Addresses")
        else:
            axes[1].set_title("Active Addresses - No Data")

        if "supply" in df.columns and not df["supply"].dropna().empty:
            axes[2].plot(df.index, df["supply"])
            axes[2].set_title("Circulating Supply")
        else:
            axes[2].set_title("Circulating Supply - No Data")

        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close(fig)
        logging.info(f"Saved raw core data plot to {plot_path}")
    except Exception as e:
        logging.error(f"Failed to generate raw core data plot: {e}", exc_info=True)


def ensure_raw_data_exists(
    plot_diagnostics: bool = True, filename: str = "raw_core_data_plot.png"
) -> bool:
    """Checks if raw parquet files exist. If not, fetches data and creates them.

    Fetches ETH price, active addresses, supply, transaction count, and fees
    if corresponding parquet files are missing in the data directory. Optionally
    plots core data diagnostics.

    Args:
        plot_diagnostics (bool): Whether to generate the diagnostic plot. Defaults to True.
        filename (str): The filename for the diagnostic plot if generated.
                        Defaults to "raw_core_data_plot.png".

    Returns:
        bool: True if all required raw data exists or was successfully created,
              False otherwise.
    """
    logging.info("Ensuring raw data files exist...")
    core_path = settings.DATA_DIR / "eth_core.parquet"
    tx_path = settings.DATA_DIR / "eth_tx.parquet"
    fee_path = settings.DATA_DIR / "eth_fee.parquet"

    # Check if ALL essential files exist
    if core_path.exists() and tx_path.exists() and fee_path.exists():
        logging.info("Raw data files found.")
        return True

    logging.warning(
        "One or more raw data files missing. Attempting to fetch and create..."
    )

    try:
        # Fetch core components (uses cache internally if available)
        logging.info("Fetching ETH price...")
        price_df = fetch_eth_price_rapidapi()  # Returns DataFrame
        if price_df.empty:
            logging.warning(
                "ETH price fetch returned empty DataFrame. Core data might be incomplete."
            )
            # Create empty df to allow merge to proceed but result might be unusable
            price_df = pd.DataFrame(columns=["price_usd"], index=pd.to_datetime([]))

        logging.info("Fetching ETH active addresses...")
        active_series = cm_fetch("AdrActCnt").rename("active_addr")
        logging.info("Fetching ETH supply...")
        supply_series = cm_fetch("SplyCur").rename("supply")

        # Combine core data
        logging.info("Combining and aligning core data...")
        # Use outer join to keep all dates initially, then align
        core_df = pd.concat(
            [price_df, active_series, supply_series], axis=1, join="outer"
        )

        # Forward fill missing values - crucial for daily data alignment
        core_df = core_df.ffill()

        # Drop rows where price is still NaN (essential)
        core_df = core_df.dropna(subset=["price_usd"])

        if core_df.empty:
            logging.error(
                "Core DataFrame is empty after fetching and cleaning. Cannot create raw files."
            )
            return False

        # Save core data
        core_df.reset_index(names="time").to_parquet(core_path, index=False)
        logging.info(f"Saved raw core data to {core_path} ({core_df.shape})")

        if plot_diagnostics:
            _plot_core_data(core_df, filename=filename)

        # Fetch and save extra metrics
        logging.info("Fetching ETH transaction count...")
        tx_series = cm_fetch("TxCnt").rename("tx_count")
        tx_series.to_frame().reset_index(names="time").to_parquet(tx_path, index=False)
        logging.info(f"Saved raw tx data to {tx_path} ({tx_series.shape})")

        logging.info("Fetching ETH total native fees...")
        # Determine correct fee metric name (handle potential variations)
        fee_metric = "FeeTotNtv"  # Default
        # Add logic here if FeeTotNtv fails, try FeeBurnNtv etc. if needed
        fee_series = cm_fetch(fee_metric).rename("fee_native")  # Keep consistent name
        fee_series.to_frame().reset_index(names="time").to_parquet(
            fee_path, index=False
        )
        logging.info(f"Saved raw fee data to {fee_path} ({fee_series.shape})")

        logging.info("Raw data fetching and saving complete.")
        return True

    except Exception as e:
        logging.error(f"Failed to fetch or save raw data: {e}", exc_info=True)
        return False


# --- Data Loading and Merging ---


def load_raw_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads the raw core, fee, and transaction parquet files.

    Loads 'eth_core.parquet', 'eth_fee.parquet', and 'eth_tx.parquet' from
    the data directory specified in settings. Renames the fee column to 'burn'.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: A tuple containing
            the core, fee (burn), and transaction DataFrames.

    Raises:
        FileNotFoundError: If any of the raw parquet files are not found.
        ValueError: If required columns are missing or fee column cannot be identified.
    """
    logging.info("Loading raw parquet files...")
    try:
        core_path = settings.DATA_DIR / "eth_core.parquet"
        fee_path = settings.DATA_DIR / "eth_fee.parquet"
        tx_path = settings.DATA_DIR / "eth_tx.parquet"

        core_df = load_parquet(core_path, ["price_usd", "active_addr", "supply"])
        logging.info("Loaded core data: %s rows", core_df.shape[0])

        fee_df = load_parquet(fee_path)
        # Find the correct fee/burn column case-insensitively
        fee_col_options = {"feeburnntv", "feetotntv", "fee_native", "burn"}
        burn_col = next(
            (c for c in fee_df.columns if c.lower() in fee_col_options), None
        )
        if burn_col is None:
            raise ValueError(
                f"Could not find a fee/burn column in {fee_path.name}. Found: {fee_df.columns.tolist()}"
            )
        fee_df = fee_df[[burn_col]].rename(columns={burn_col: "burn"})
        logging.info("Loaded fee data: %s rows", fee_df.shape[0])

        tx_df = load_parquet(tx_path, ["tx_count"])
        logging.info("Loaded tx data: %s rows", tx_df.shape[0])

        return core_df, fee_df, tx_df

    except FileNotFoundError as e:
        logging.error(f"Raw data file not found: {e}. Run initial data fetching first.")
        raise
    except ValueError as e:
        logging.error(f"Error loading raw data: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading raw data: {e}", exc_info=True)
        raise


def merge_eth_data(
    core_df: pd.DataFrame, fee_df: pd.DataFrame, tx_df: pd.DataFrame
) -> pd.DataFrame:
    """Merges core, fee (burn), and transaction data into a single DataFrame.

    Performs left joins starting from the core DataFrame. Fills NaN values in
    the 'burn' column with 0.0 and calculates 'market_cap'.

    Args:
        core_df (pd.DataFrame): DataFrame with core ETH data (price, active_addr, supply).
        fee_df (pd.DataFrame): DataFrame with ETH fee/burn data (renamed to 'burn').
        tx_df (pd.DataFrame): DataFrame with ETH transaction count data.

    Returns:
        pd.DataFrame: The merged DataFrame containing all input data plus 'market_cap'.
    """
    logging.info("Joining ETH datasets...")
    # Ensure indices are compatible (should be datetime already)
    # Perform left joins starting from core_df
    df = core_df.join(fee_df, how="left").join(tx_df, how="left")

    # Fill NaNs introduced by joins (especially for 'burn') before calculating market_cap
    df["burn"] = df["burn"].fillna(0.0)
    # Calculate market cap
    df["market_cap"] = df["price_usd"] * df["supply"]

    logging.info("Initial merged df shape: %s", df.shape)
    # Check for unexpected NaNs in core columns after merge
    core_cols = ["price_usd", "active_addr", "supply", "market_cap"]
    if df[core_cols].isnull().any().any():
        logging.warning(
            f"NaNs found in core columns after merge: \n{df[core_cols].isnull().sum()}"
        )
        # Optional: Decide whether to drop these rows here or let later steps handle it
        # df = df.dropna(subset=core_cols)
        # logging.info("Shape after dropping rows with NaNs in core columns: %s", df.shape)

    return df


def align_nasdaq_data(eth_df: pd.DataFrame) -> pd.DataFrame:
    """Fetches/loads NASDAQ data, aligns it, and joins it to the ETH DataFrame.

    Fetches NASDAQ (^NDX) data using fetch_nasdaq (which utilizes caching).
    Resamples NASDAQ data to daily frequency using forward fill. Aligns the
    daily NASDAQ data to the date range of the input eth_df and joins it
    as a new 'nasdaq' column.

    Args:
        eth_df (pd.DataFrame): The DataFrame containing merged ETH data.

    Returns:
        pd.DataFrame: The input DataFrame with an added 'nasdaq' column,
                      aligned and forward-filled. Returns the original DataFrame
                      with a NaN 'nasdaq' column if NASDAQ fetching/alignment fails.
    """
    logging.info("Fetching/Loading NASDAQ data...")
    try:
        ndx_raw = fetch_nasdaq()  # Uses cache via decorator
        if ndx_raw.empty:
            logging.warning("Fetched NASDAQ data is empty. Proceeding without NASDAQ.")
            eth_df["nasdaq"] = np.nan  # Add an empty column
            return eth_df
        logging.info("Raw NASDAQ data shape: %s", ndx_raw.shape)

        # Align NASDAQ data to the main DataFrame's index range
        min_eth_date = eth_df.index.min()
        max_eth_date = eth_df.index.max()
        logging.info("Aligning NASDAQ data from %s to %s", min_eth_date, max_eth_date)

        # Forward-fill on a daily frequency *before* slicing
        ndx_raw = ndx_raw.sort_index()  # Ensure sorted
        # Create a full daily index from the start of NASDAQ to max_eth_date
        full_daily_index = pd.date_range(
            start=ndx_raw.index.min(), end=max_eth_date, freq="D"
        )
        # Reindex NASDAQ data to this full index, then forward fill
        ndx_daily = ndx_raw.reindex(full_daily_index).ffill()
        # Now slice based on the eth_df index range
        ndx_daily_aligned = ndx_daily.loc[min_eth_date:max_eth_date]
        logging.info(
            "Daily NASDAQ data shape after alignment: %s", ndx_daily_aligned.shape
        )

        logging.info("Joining NASDAQ data into main DataFrame...")
        df_with_nasdaq = eth_df.join(
            ndx_daily_aligned.rename("nasdaq")
        )  # Ensure name is 'nasdaq'

        # Check for NaNs introduced by NASDAQ join within the ETH range
        nasdaq_nan_count = (
            df_with_nasdaq["nasdaq"].loc[min_eth_date:max_eth_date].isnull().sum()
        )
        if nasdaq_nan_count > 0:
            logging.warning(
                "NASDAQ column has %s NaNs after join and ffill within the ETH data range.",
                nasdaq_nan_count,
            )
            # Optional: Backfill remaining NaNs if desired
            # df_with_nasdaq['nasdaq'] = df_with_nasdaq['nasdaq'].bfill()
            # logging.info("Backfilled remaining NASDAQ NaNs.")

        # Check if all NASDAQ values are NaN (e.g., if date ranges didn't overlap)
        if df_with_nasdaq["nasdaq"].isnull().all():
            logging.warning(
                "All NASDAQ values are NaN after alignment. Check date ranges."
            )

        return df_with_nasdaq

    except Exception as e:
        logging.error(f"Failed to fetch or align NASDAQ data: {e}", exc_info=True)
        # Return the original dataframe with an empty nasdaq column on error
        eth_df["nasdaq"] = np.nan
        return eth_df


# --- Feature Engineering and Cleaning ---


def engineer_log_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates log-transformed features for key variables.

    Computes natural logarithms for 'market_cap', 'active_addr', and 'nasdaq'.
    Uses log(1 + x) for 'burn' to handle potential zero values. Replaces
    any resulting infinities with NaN.

    Args:
        df (pd.DataFrame): DataFrame containing the original features
                           ('market_cap', 'active_addr', 'burn', 'nasdaq').

    Returns:
        pd.DataFrame: The input DataFrame with added log-transformed columns:
                      'log_marketcap', 'log_active', 'log_gas', 'log_nasdaq'.
    """
    logging.info("Calculating log-scale features...")
    df_out = df.copy()  # Avoid modifying original df

    # Use np.log1p for columns that can be zero (like burn)
    # Use np.log for columns that should be strictly positive (handle errors)
    with np.errstate(divide="ignore", invalid="ignore"):  # Suppress log(0) warnings
        df_out["log_marketcap"] = np.log(df_out["market_cap"].replace(0, np.nan))
        df_out["log_active"] = np.log(df_out["active_addr"].replace(0, np.nan))
        df_out["log_gas"] = np.log1p(df_out["burn"])  # log1p handles burn=0
        df_out["log_nasdaq"] = np.log(df_out["nasdaq"].replace(0, np.nan))

    # Replace any -inf/inf resulting from logs of non-positive numbers with NaN
    df_out.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Log how many NaNs were introduced or already present in log columns
    log_cols = ["log_marketcap", "log_active", "log_gas", "log_nasdaq"]
    nan_counts = df_out[log_cols].isnull().sum()
    if nan_counts.any():
        logging.warning(
            f"NaNs found in log columns after calculation: \n{nan_counts[nan_counts > 0]}"
        )

    return df_out


def create_daily_clean(df_with_logs: pd.DataFrame) -> pd.DataFrame:
    """Creates the cleaned daily DataFrame by dropping rows with essential NaNs.

    Drops rows where 'log_marketcap' or 'log_active' are NaN.

    Args:
        df_with_logs (pd.DataFrame): DataFrame containing log-transformed features.

    Returns:
        pd.DataFrame: The cleaned daily DataFrame. Can be empty if all rows
                      have NaNs in essential columns.
    """
    logging.info("Creating daily_clean DataFrame...")
    # Define core columns needed for analysis AFTER log transformation
    # Minimum requirement: log_marketcap and log_active must be present
    essential_log_cols = ["log_marketcap", "log_active"]
    daily_clean = df_with_logs.dropna(subset=essential_log_cols)

    logging.info(
        "daily_clean shape after dropping NaNs in essential columns: %s",
        daily_clean.shape,
    )
    if daily_clean.empty:
        logging.warning("daily_clean DataFrame is empty after dropping NaNs.")

    return daily_clean


def create_monthly_clean(df_with_logs: pd.DataFrame) -> pd.DataFrame:
    """Resamples daily data to month-end, recalculates log features, and cleans.

    Resamples the input DataFrame to month-end ('ME') frequency using the mean
    of numeric columns. Recalculates log features on the monthly averages.
    Drops months where any of the core log features ('log_marketcap',
    'log_active', 'log_gas', 'log_nasdaq') are NaN.

    Args:
        df_with_logs (pd.DataFrame): The daily DataFrame *with* log features already
                                     calculated (used for resampling base values).

    Returns:
        pd.DataFrame: The cleaned monthly DataFrame. Can be empty if input is empty
                      or if all resampled rows have NaNs in essential log columns.
    """
    logging.info("Resampling to month-end frequency...")
    if df_with_logs.empty:
        logging.warning(
            "Input DataFrame for monthly resampling is empty. Returning empty DataFrame."
        )
        return pd.DataFrame()

    # Resample using mean. Note: resampling before log transform differs from resampling after.
    # Original script resampled originals then took logs. Let's follow that.
    # Ensure only numeric columns are used in mean calculation
    numeric_cols = df_with_logs.select_dtypes(include=np.number).columns
    monthly = df_with_logs[numeric_cols].resample("ME").mean()  # 'ME' for Month End

    # Recalculate logs based on monthly averages
    monthly_with_logs = engineer_log_features(monthly)  # Reuse log feature engineering

    # Define core log columns required for monthly analysis
    core_monthly_log_cols = ["log_marketcap", "log_active", "log_gas", "log_nasdaq"]

    # Drop months where any core log feature is NaN
    monthly_clean = monthly_with_logs.dropna(subset=core_monthly_log_cols)
    logging.info("monthly_clean shape after dropna: %s", monthly_clean.shape)

    if monthly_clean.empty:
        logging.warning(
            "monthly_clean DataFrame is empty after resampling and cleaning."
        )
    elif len(monthly_clean) < 24:
        logging.warning(
            "Monthly data has only %s rows, may be insufficient for some analyses.",
            len(monthly_clean),
        )

    return monthly_clean


# --- Orchestration Function ---


def process_all_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Loads raw data, merges, adds features, cleans, and saves processed files.

    Orchestrates the entire data processing pipeline:
    1. Loads raw core, fee, and transaction data.
    2. Merges the ETH-specific datasets.
    3. Fetches, aligns, and joins NASDAQ data.
    4. Engineers log-transformed features.
    5. Creates the final cleaned daily DataFrame.
    6. Creates the final cleaned monthly DataFrame (by resampling daily).
    7. Saves the cleaned daily and monthly DataFrames to parquet files
       ('daily_clean.parquet', 'monthly_clean.parquet') in the data directory.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing the cleaned daily
            and monthly DataFrames. Returns empty DataFrames if processing fails.
    """
    try:
        # 1. Load
        core_df, fee_df, tx_df = load_raw_data()

        # 2. Merge ETH Data
        merged_df = merge_eth_data(core_df, fee_df, tx_df)
        if merged_df.empty:
            logging.error("Merged ETH DataFrame is empty. Cannot proceed.")
            return pd.DataFrame(), pd.DataFrame()  # Return empty frames

        # 3. Add NASDAQ
        df_with_nasdaq = align_nasdaq_data(merged_df)

        # 4. Engineer Log Features
        df_with_logs = engineer_log_features(df_with_nasdaq)

        # 5. Create Clean Daily Frame
        daily_clean = create_daily_clean(df_with_logs)

        # 6. Create Clean Monthly Frame (use df_with_logs before daily cleaning)
        monthly_clean = create_monthly_clean(df_with_logs)

        # 7. Save Processed DataFrames
        logging.info("Saving processed DataFrames...")
        daily_clean_path = settings.DATA_DIR / "daily_clean.parquet"
        monthly_clean_path = settings.DATA_DIR / "monthly_clean.parquet"

        daily_clean.to_parquet(daily_clean_path)
        monthly_clean.to_parquet(monthly_clean_path)
        logging.info(f"Saved daily_clean to {daily_clean_path} ({daily_clean.shape})")
        logging.info(
            f"Saved monthly_clean to {monthly_clean_path} ({monthly_clean.shape})"
        )

        return daily_clean, monthly_clean

    except Exception as e:
        logging.error(f"Error in process_all_data: {e}", exc_info=True)
        # Return empty dataframes on failure
        return pd.DataFrame(), pd.DataFrame()
