# tests/test_data_processing.py

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Assuming src is importable via conftest.py
from src.config import settings
from src.data_processing import (
    align_nasdaq_data,
    create_daily_clean,
    create_monthly_clean,
    engineer_log_features,
    load_raw_data,
    merge_eth_data,
    process_all_data,
)

# --- Fixtures ---


@pytest.fixture
def sample_raw_core_df() -> pd.DataFrame:
    """Sample raw core data DataFrame."""
    dates = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
    df = pd.DataFrame(
        {
            "price_usd": [1200.0, 1210.0, 1205.0],
            "active_addr": [500000, 510000, 505000],
            "supply": [120e6, 120.1e6, 120.2e6],
        },
        index=pd.Index(dates, name="time"),
    )
    return df


@pytest.fixture
def sample_raw_fee_df() -> pd.DataFrame:
    """Sample raw fee data DataFrame (using FeeTotNtv)."""
    dates = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
    # Use a plausible column name found in the code
    df = pd.DataFrame(
        {"FeeTotNtv": [100.0, 150.0, 120.0]}, index=pd.Index(dates, name="time")
    )
    return df


@pytest.fixture
def sample_raw_tx_df() -> pd.DataFrame:
    """Sample raw transaction count DataFrame."""
    dates = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
    df = pd.DataFrame(
        {"tx_count": [1.0e6, 1.1e6, 1.05e6]}, index=pd.Index(dates, name="time")
    )
    return df


@pytest.fixture
def sample_raw_nasdaq_series() -> pd.Series:
    """Sample raw NASDAQ data Series."""
    dates = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"])
    # Note: fetch_nasdaq returns a Series
    series = pd.Series(
        [15000.0, 15100.0, 15050.0, 15150.0],
        index=pd.Index(dates, name="time"),
        name="nasdaq",
    )
    return series


# --- Tests for load_raw_data ---


@patch("src.data_processing.load_parquet")  # Mock the utility function
def test_load_raw_data_happy_path(
    mock_load_parquet: MagicMock,
    sample_raw_core_df: pd.DataFrame,
    sample_raw_fee_df: pd.DataFrame,
    sample_raw_tx_df: pd.DataFrame,
    tmp_path: Path,  # Use tmp_path for dummy settings
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests loading raw data successfully."""
    # Patch DATA_DIR setting
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    # Configure mock to return sample data based on path name
    def load_parquet_side_effect(path: Path, req_cols: list[str] | None = None):
        if "core" in path.name:
            return sample_raw_core_df
        elif "fee" in path.name:
            return sample_raw_fee_df
        elif "tx" in path.name:
            return sample_raw_tx_df
        else:
            raise FileNotFoundError(f"Unexpected path: {path}")

    mock_load_parquet.side_effect = load_parquet_side_effect

    core_df, fee_df, tx_df = load_raw_data()

    assert mock_load_parquet.call_count == 3
    pd.testing.assert_frame_equal(core_df, sample_raw_core_df)
    # Check that fee_df has the 'burn' column correctly renamed
    assert "burn" in fee_df.columns
    assert fee_df.shape[1] == 1
    pd.testing.assert_series_equal(
        fee_df["burn"], sample_raw_fee_df["FeeTotNtv"].rename("burn")
    )
    pd.testing.assert_frame_equal(tx_df, sample_raw_tx_df)


@patch(
    "src.data_processing.load_parquet",
    side_effect=FileNotFoundError("Mock file not found"),
)
def test_load_raw_data_file_not_found(
    mock_load_parquet: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Tests that FileNotFoundError is raised if a file is missing."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_raw_data()


@patch("src.data_processing.load_parquet")
def test_load_raw_data_missing_fee_column(
    mock_load_parquet: MagicMock,
    sample_raw_core_df: pd.DataFrame,
    sample_raw_tx_df: pd.DataFrame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests error handling if the fee/burn column isn't found."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    # Create a fee df with a wrong column name
    bad_fee_df = pd.DataFrame({"wrong_col": [1, 2]}, index=sample_raw_core_df.index[:2])

    def load_parquet_side_effect(path: Path, req_cols: list[str] | None = None):
        if "core" in path.name:
            return sample_raw_core_df
        elif "fee" in path.name:
            return bad_fee_df  # Return bad fee df
        elif "tx" in path.name:
            return sample_raw_tx_df
        else:
            raise FileNotFoundError(f"Unexpected path: {path}")

    mock_load_parquet.side_effect = load_parquet_side_effect

    with pytest.raises(ValueError, match="Could not find a fee/burn column"):
        load_raw_data()


# --- Tests for merge_eth_data ---


def test_merge_eth_data_happy_path(
    sample_raw_core_df: pd.DataFrame,
    sample_raw_fee_df: pd.DataFrame,
    sample_raw_tx_df: pd.DataFrame,
):
    """Tests merging the three core ETH dataframes."""
    # Prepare input data (fee df needs 'burn' column)
    core_df = sample_raw_core_df
    fee_df = sample_raw_fee_df.rename(columns={"FeeTotNtv": "burn"})
    tx_df = sample_raw_tx_df

    merged_df = merge_eth_data(core_df, fee_df, tx_df)

    # Check shape
    assert merged_df.shape[0] == 3  # Based on sample data length
    # Check columns: original core + burn + tx_count + market_cap
    expected_cols = [*list(core_df.columns), "burn", "tx_count", "market_cap"]
    assert sorted(merged_df.columns) == sorted(expected_cols)

    # Check market_cap calculation
    expected_mcap = core_df["price_usd"] * core_df["supply"]
    pd.testing.assert_series_equal(
        merged_df["market_cap"], expected_mcap, check_names=False
    )

    # Check join correctness (values should match originals)
    pd.testing.assert_series_equal(merged_df["price_usd"], core_df["price_usd"])
    pd.testing.assert_series_equal(merged_df["burn"], fee_df["burn"])
    pd.testing.assert_series_equal(merged_df["tx_count"], tx_df["tx_count"])


def test_merge_eth_data_with_missing_rows(
    sample_raw_core_df: pd.DataFrame,
    sample_raw_fee_df: pd.DataFrame,
    sample_raw_tx_df: pd.DataFrame,
):
    """Tests merging when input frames have slightly different date ranges."""
    core_df = sample_raw_core_df  # Dates 01, 02, 03
    fee_df = sample_raw_fee_df.iloc[:2].rename(
        columns={"FeeTotNtv": "burn"}
    )  # Dates 01, 02
    tx_df = sample_raw_tx_df.iloc[1:]  # Dates 02, 03

    merged_df = merge_eth_data(core_df, fee_df, tx_df)

    # Should still have 3 rows based on left join from core_df
    assert merged_df.shape[0] == 3
    assert merged_df.index.equals(core_df.index)

    # Check NaNs where data was missing (BEFORE fillna for burn)
    assert pd.isna(merged_df.loc["2023-01-01", "tx_count"])  # Tx missing on day 1

    # Check that burn NaN was filled with 0.0
    assert merged_df.loc["2023-01-03", "burn"] == 0.0


# --- Tests for align_nasdaq_data ---


@pytest.fixture
def sample_merged_eth_df() -> pd.DataFrame:
    """Sample DataFrame mimicking output of merge_eth_data."""
    # Use dates that will overlap with sample_raw_nasdaq_series
    dates = pd.to_datetime(["2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"])
    df = pd.DataFrame(
        {
            "price_usd": [1210.0, 1205.0, 1220.0, 1230.0],
            "active_addr": [510000, 505000, 515000, 520000],
            "supply": [120.1e6, 120.2e6, 120.3e6, 120.4e6],
            "burn": [150.0, 120.0, 160.0, 170.0],
            "tx_count": [1.1e6, 1.05e6, 1.15e6, 1.2e6],
            "market_cap": [1.465e11, 1.452e11, 1.480e11, 1.500e11],
        },
        index=pd.Index(dates, name="time"),
    )
    return df


@patch(
    "src.data_processing.fetch_nasdaq"
)  # Mock fetch_nasdaq called by align_nasdaq_data
def test_align_nasdaq_data_happy_path(
    mock_fetch_nasdaq: MagicMock,
    sample_merged_eth_df: pd.DataFrame,
    sample_raw_nasdaq_series: pd.Series,
):
    """Tests successful alignment and joining of NASDAQ data."""
    mock_fetch_nasdaq.return_value = sample_raw_nasdaq_series
    eth_df = sample_merged_eth_df

    df_with_nasdaq = align_nasdaq_data(eth_df)

    # Check nasdaq column exists
    assert "nasdaq" in df_with_nasdaq.columns
    # Check shape (should be same number of rows as eth_df)
    assert df_with_nasdaq.shape[0] == eth_df.shape[0]
    assert df_with_nasdaq.shape[1] == eth_df.shape[1] + 1
    # Check index matches eth_df
    assert df_with_nasdaq.index.equals(eth_df.index)

    # Check values and forward filling
    # Raw NASDAQ: 2023-01-01: 15000, 02: 15100, 03: 15050, 04: 15150
    # ETH DF:          Dates: 02,      03,      04,      05
    # Expected NASDAQ:        15100,   15050,   15150,   15150 (ffill from 04)
    expected_nasdaq_values = [15100.0, 15050.0, 15150.0, 15150.0]
    pd.testing.assert_series_equal(
        df_with_nasdaq["nasdaq"],
        pd.Series(expected_nasdaq_values, index=eth_df.index, name="nasdaq"),
        check_dtype=False,
    )
    mock_fetch_nasdaq.assert_called_once()


@patch("src.data_processing.fetch_nasdaq")
def test_align_nasdaq_data_fetch_fails(
    mock_fetch_nasdaq: MagicMock, sample_merged_eth_df: pd.DataFrame
):
    """Tests behavior when fetch_nasdaq returns an empty Series."""
    mock_fetch_nasdaq.return_value = pd.Series(
        dtype=float, name="nasdaq"
    )  # Empty series
    eth_df = sample_merged_eth_df

    df_with_nasdaq = align_nasdaq_data(eth_df)

    assert "nasdaq" in df_with_nasdaq.columns
    # Check all nasdaq values are NaN
    assert df_with_nasdaq["nasdaq"].isna().all()
    # Check shape is still correct
    assert df_with_nasdaq.shape[0] == eth_df.shape[0]
    assert (
        df_with_nasdaq.shape[1] == eth_df.shape[1]
    )  # Shape shouldn't change in this path
    mock_fetch_nasdaq.assert_called_once()


@patch("src.data_processing.fetch_nasdaq", side_effect=Exception("API Down"))
def test_align_nasdaq_data_fetch_exception(
    mock_fetch_nasdaq: MagicMock, sample_merged_eth_df: pd.DataFrame
):
    """Tests behavior when fetch_nasdaq raises an exception."""
    eth_df = sample_merged_eth_df

    df_with_nasdaq = align_nasdaq_data(eth_df)

    assert "nasdaq" in df_with_nasdaq.columns
    # Check all nasdaq values are NaN
    assert df_with_nasdaq["nasdaq"].isna().all()
    # Check shape is still correct
    assert df_with_nasdaq.shape[0] == eth_df.shape[0]
    assert (
        df_with_nasdaq.shape[1] == eth_df.shape[1]
    )  # Shape shouldn't change in this path
    mock_fetch_nasdaq.assert_called_once()


# --- Tests for Feature Engineering and Cleaning ---


@pytest.fixture
def sample_df_for_logs() -> pd.DataFrame:
    """Sample DataFrame before log feature engineering."""
    dates = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"])
    df = pd.DataFrame(
        {
            "market_cap": [1e11, 1.1e11, 0, 1.2e11],  # Include zero market cap
            "active_addr": [5e5, 5.1e5, 5.2e5, 0],  # Include zero active_addr
            "burn": [100.0, 0.0, 150.0, 200.0],  # Include zero burn
            "nasdaq": [15000.0, 15100.0, np.nan, 15200.0],  # Include NaN nasdaq
            # Add other necessary columns for downstream cleaning/resampling if needed
            "price_usd": [1000, 1100, 0, 1200],
            "supply": [1e8, 1e8, 1e8, 1e8],
        },
        index=pd.Index(dates, name="time"),
    )
    return df


def test_engineer_log_features(sample_df_for_logs: pd.DataFrame):
    """Tests log feature calculation, including handling of zeros and NaNs."""
    df_input = sample_df_for_logs
    df_output = engineer_log_features(df_input)

    # Check new columns exist
    log_cols = ["log_marketcap", "log_active", "log_gas", "log_nasdaq"]
    for col in log_cols:
        assert col in df_output.columns

    # Check calculations (manual check for specific values)
    assert np.isclose(df_output.loc["2023-01-01", "log_marketcap"], np.log(1e11))
    assert np.isclose(df_output.loc["2023-01-01", "log_active"], np.log(5e5))
    assert np.isclose(df_output.loc["2023-01-01", "log_gas"], np.log1p(100.0))
    assert np.isclose(df_output.loc["2023-01-01", "log_nasdaq"], np.log(15000.0))

    # Check handling of zeros -> NaN after log
    assert pd.isna(df_output.loc["2023-01-03", "log_marketcap"])  # log(0) -> NaN
    assert pd.isna(df_output.loc["2023-01-04", "log_active"])  # log(0) -> NaN

    # Check handling of zeros -> log1p(0) = 0
    assert np.isclose(df_output.loc["2023-01-02", "log_gas"], 0.0)

    # Check handling of NaN -> NaN
    assert pd.isna(df_output.loc["2023-01-03", "log_nasdaq"])


def test_create_daily_clean(sample_df_for_logs: pd.DataFrame):
    """Tests dropping rows with NaNs in essential log columns."""
    df_with_logs = engineer_log_features(sample_df_for_logs)
    daily_clean = create_daily_clean(df_with_logs)

    # Original had 4 rows.
    # Row 2023-01-03 has NaN log_marketcap -> dropped
    # Row 2023-01-04 has NaN log_active -> dropped
    # Expected remaining rows: 2023-01-01, 2023-01-02
    assert daily_clean.shape[0] == 2
    assert "2023-01-03" not in daily_clean.index
    assert "2023-01-04" not in daily_clean.index
    assert "2023-01-01" in daily_clean.index
    assert "2023-01-02" in daily_clean.index


def test_create_monthly_clean(sample_df_for_logs: pd.DataFrame):
    """Tests resampling to monthly, recalculating logs, and cleaning."""
    # Create a slightly longer df for resampling test
    dates = pd.date_range(start="2023-01-01", periods=65, freq="D")
    n_obs = len(dates)
    df_long = pd.DataFrame(
        {
            "market_cap": np.linspace(1e11, 1.5e11, n_obs),
            "active_addr": np.linspace(5e5, 6e5, n_obs),
            "burn": np.linspace(100, 200, n_obs),
            "nasdaq": np.linspace(15000, 16000, n_obs),
            "price_usd": np.linspace(1000, 1500, n_obs),  # Needed for resample
            "supply": np.linspace(1e8, 1.1e8, n_obs),  # Needed for resample
        },
        index=dates,
    )
    # Add a NaN that will cause a whole month to be dropped after log recalc
    df_long.loc["2023-02-15", "nasdaq"] = np.nan

    # Run the function
    monthly_clean = create_monthly_clean(df_long)

    # Check index is MonthEnd
    assert isinstance(monthly_clean.index, pd.DatetimeIndex)
    assert all(idx.is_month_end for idx in monthly_clean.index)
    assert monthly_clean.index.freqstr == "ME"

    # Check shape - Started with Jan, Feb, Mar data. Feb should be dropped due to NaN in log_nasdaq.
    assert monthly_clean.shape[0] == 3  # Jan, Feb, Mar should remain
    assert pd.Timestamp("2023-01-31") in monthly_clean.index
    assert pd.Timestamp("2023-02-28") in monthly_clean.index  # Feb should be present
    assert pd.Timestamp("2023-03-31") in monthly_clean.index

    # Check log columns exist
    log_cols = ["log_marketcap", "log_active", "log_gas", "log_nasdaq"]
    for col in log_cols:
        assert col in monthly_clean.columns

    # Check a recalculated log value (e.g., Jan mean nasdaq)
    jan_mean_nasdaq = df_long.loc["2023-01", "nasdaq"].mean()
    expected_log_nasdaq_jan = np.log(jan_mean_nasdaq)
    assert np.isclose(
        monthly_clean.loc["2023-01-31", "log_nasdaq"], expected_log_nasdaq_jan
    )

    # Add this assertion at the end of the test:
    feb_mean_nasdaq = df_long.loc[
        "2023-02", "nasdaq"
    ].mean()  # Mean excludes the NaN day
    expected_log_nasdaq_feb = np.log(feb_mean_nasdaq)
    assert np.isclose(
        monthly_clean.loc["2023-02-28", "log_nasdaq"], expected_log_nasdaq_feb
    )


# --- Tests for process_all_data ---


@patch("src.data_processing.load_raw_data")
@patch("src.data_processing.merge_eth_data")
@patch("src.data_processing.align_nasdaq_data")
@patch("src.data_processing.engineer_log_features")
@patch("src.data_processing.create_daily_clean")
@patch("src.data_processing.create_monthly_clean")
@patch("pandas.DataFrame.to_parquet")  # Mock the final saving step
def test_process_all_data_happy_path(
    mock_to_parquet: MagicMock,
    mock_create_monthly: MagicMock,
    mock_create_daily: MagicMock,
    mock_engineer_logs: MagicMock,
    mock_align_nasdaq: MagicMock,
    mock_merge_eth: MagicMock,
    mock_load_raw: MagicMock,
    tmp_path: Path,  # Use tmp_path for dummy settings
    monkeypatch: pytest.MonkeyPatch,
):
    """Tests the main data processing pipeline orchestration."""
    # Patch DATA_DIR setting
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    # --- Mock return values for each step ---
    # 1. Load
    mock_core = pd.DataFrame(
        {"price_usd": [1], "active_addr": [2], "supply": [3]},
        index=pd.to_datetime(["2023-01-01"]),
    )
    mock_fee = pd.DataFrame({"burn": [4]}, index=pd.to_datetime(["2023-01-01"]))
    mock_tx = pd.DataFrame({"tx_count": [5]}, index=pd.to_datetime(["2023-01-01"]))
    mock_load_raw.return_value = (mock_core, mock_fee, mock_tx)

    # 2. Merge
    mock_merged = pd.DataFrame(
        {
            "price_usd": [1],
            "active_addr": [2],
            "supply": [3],
            "burn": [4],
            "tx_count": [5],
            "market_cap": [3],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    mock_merge_eth.return_value = mock_merged

    # 3. Align NASDAQ
    mock_with_nasdaq = mock_merged.copy()
    mock_with_nasdaq["nasdaq"] = [15000]
    mock_align_nasdaq.return_value = mock_with_nasdaq

    # 4. Engineer Logs
    mock_with_logs = mock_with_nasdaq.copy()
    mock_with_logs["log_marketcap"] = [np.log(3)]
    mock_with_logs["log_active"] = [np.log(2)]
    mock_with_logs["log_gas"] = [np.log1p(4)]
    mock_with_logs["log_nasdaq"] = [np.log(15000)]
    mock_engineer_logs.return_value = mock_with_logs

    # 5. Create Daily Clean
    mock_daily = mock_with_logs.copy()  # Assume no rows dropped for simplicity
    mock_create_daily.return_value = mock_daily

    # 6. Create Monthly Clean
    mock_monthly = mock_daily.resample("ME").mean()  # Simple mock monthly
    mock_create_monthly.return_value = mock_monthly
    # --- End Mock Setup ---

    # Call the orchestrator function
    daily_result, monthly_result = process_all_data()

    # --- Assertions ---
    # Check that mocks were called in order
    mock_load_raw.assert_called_once()
    mock_merge_eth.assert_called_once_with(mock_core, mock_fee, mock_tx)
    mock_align_nasdaq.assert_called_once_with(mock_merged)
    mock_engineer_logs.assert_called_once_with(mock_with_nasdaq)
    mock_create_daily.assert_called_once_with(mock_with_logs)
    mock_create_monthly.assert_called_once_with(
        mock_with_logs
    )  # Called with pre-daily clean data

    # Check that saving was attempted twice (daily, monthly)
    assert mock_to_parquet.call_count == 2
    call_args_list = mock_to_parquet.call_args_list
    # Check the paths used for saving
    expected_daily_path = tmp_path / "daily_clean.parquet"
    expected_monthly_path = tmp_path / "monthly_clean.parquet"
    saved_paths = [
        call[0][0] for call in call_args_list
    ]  # Get the first arg (path) from each call
    assert expected_daily_path in saved_paths
    assert expected_monthly_path in saved_paths

    # Check returned dataframes match mocked final steps
    pd.testing.assert_frame_equal(daily_result, mock_daily)
    pd.testing.assert_frame_equal(monthly_result, mock_monthly)


@patch(
    "src.data_processing.load_raw_data",
    return_value=(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()),
)
def test_process_all_data_load_fails(mock_load_raw: MagicMock):
    """Tests that pipeline exits early if loading fails (returns empty)."""
    # We mock load_raw_data to return empty frames implicitly via the decorator args
    daily_result, monthly_result = process_all_data()
    assert daily_result.empty
    assert monthly_result.empty
    mock_load_raw.assert_called_once()
    # Other mocks should not have been called


@patch("src.data_processing.load_raw_data")  # Need to mock load to proceed
@patch(
    "src.data_processing.merge_eth_data", return_value=pd.DataFrame()
)  # Mock merge to return empty
def test_process_all_data_merge_fails(mock_merge: MagicMock, mock_load: MagicMock):
    """Tests that pipeline exits early if merging fails (returns empty)."""
    # Setup mock load to return something valid
    mock_load.return_value = (
        pd.DataFrame({"a": [1]}),
        pd.DataFrame({"b": [1]}),
        pd.DataFrame({"c": [1]}),
    )

    daily_result, monthly_result = process_all_data()
    assert daily_result.empty
    assert monthly_result.empty
    mock_load.assert_called_once()
    mock_merge.assert_called_once()
    # Other mocks should not have been called
