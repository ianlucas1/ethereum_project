# tests/test_data_processing.py

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Assuming src is importable via conftest.py
from src.config import settings
from src.data_processing import (
    load_raw_data,
    merge_eth_data,  # Import private function for testing if needed, or mock its call
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
    expected_cols = list(core_df.columns) + ["burn", "tx_count", "market_cap"]
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
