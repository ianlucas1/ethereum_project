# tests/test_feature_engineering.py

import pandas as pd
import numpy as np
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

# Assuming src is importable via conftest.py
from src.data_processing import engineer_log_features, create_monthly_clean

# --- Test Data ---

@pytest.fixture
def sample_daily_df() -> pd.DataFrame:
    """Provides a sample DataFrame mimicking daily data before log features."""
    dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-31', '2023-02-01', '2023-02-28'])
    data = {
        'market_cap': [100.0, 110.0, 120.0, 130.0, 140.0],
        'active_addr': [10.0, 11.0, 12.0, 13.0, 14.0],
        'burn': [0.0, 1.0, 0.5, 2.0, 0.0], # Include zero burn
        'nasdaq': [1000.0, 1010.0, 1020.0, 1030.0, 1040.0],
        'price_usd': [1.0, 1.1, 1.2, 1.3, 1.4], # Needed for monthly resampling test later
        'supply': [100.0, 100.0, 100.0, 100.0, 100.0] # Needed for monthly resampling test later
    }
    return pd.DataFrame(data, index=dates)

# --- Test Cases ---

def test_engineer_log_features(sample_daily_df):
    """Tests the engineer_log_features function."""
    df_input = sample_daily_df
    df_output = engineer_log_features(df_input)

    # Check expected columns exist
    expected_log_cols = ['log_marketcap', 'log_active', 'log_gas', 'log_nasdaq']
    for col in expected_log_cols:
        assert col in df_output.columns, f"Expected log column '{col}' not found."

    # Calculate expected values manually
    expected_log_marketcap = np.log(df_input['market_cap'])
    expected_log_active = np.log(df_input['active_addr'])
    expected_log_gas = np.log1p(df_input['burn']) # Use log1p for burn
    expected_log_nasdaq = np.log(df_input['nasdaq'])

    # Assert calculated values match expected values
    assert_series_equal(df_output['log_marketcap'], expected_log_marketcap, check_names=False)
    assert_series_equal(df_output['log_active'], expected_log_active, check_names=False)
    assert_series_equal(df_output['log_gas'], expected_log_gas, check_names=False)
    assert_series_equal(df_output['log_nasdaq'], expected_log_nasdaq, check_names=False)

    # Check that original columns are still present
    for col in df_input.columns:
        assert col in df_output.columns

    # Check shape
    assert df_output.shape == (df_input.shape[0], df_input.shape[1] + len(expected_log_cols))

def test_create_monthly_clean_resampling(sample_daily_df):
    """Tests the create_monthly_clean function for correct resampling and log recalculation."""
    # First, add log features to the sample daily data
    df_daily_with_logs = engineer_log_features(sample_daily_df)

    # Run the function to create monthly data
    df_monthly = create_monthly_clean(df_daily_with_logs)

    # --- Assertions ---
    # 1. Check index is MonthEnd
    assert isinstance(df_monthly.index, pd.DatetimeIndex)
    assert all(idx.is_month_end for idx in df_monthly.index)
    assert df_monthly.index.freqstr == 'ME' # Check frequency is MonthEnd

    # 2. Check number of rows (should be 2 months: Jan, Feb)
    assert len(df_monthly) == 2

    # 3. Check resampling calculation (mean) for a non-log column
    # Jan mean market_cap = (100 + 110 + 120) / 3 = 110
    # Feb mean market_cap = (130 + 140) / 2 = 135
    expected_market_cap_monthly = pd.Series([110.0, 135.0], index=df_monthly.index, name='market_cap')
    assert_series_equal(df_monthly['market_cap'], expected_market_cap_monthly, check_dtype=False)

    # 4. Check log recalculation on monthly data
    # Jan mean active_addr = (10 + 11 + 12) / 3 = 11
    # Feb mean active_addr = (13 + 14) / 2 = 13.5
    # Expected log_active for Jan = log(11), Feb = log(13.5)
    expected_log_active_monthly = np.log(pd.Series([11.0, 13.5], index=df_monthly.index, name='log_active'))
    assert_series_equal(df_monthly['log_active'], expected_log_active_monthly, check_dtype=False)

    # 5. Check log_gas recalculation (using log1p)
    # Jan mean burn = (0.0 + 1.0 + 0.5) / 3 = 0.5
    # Feb mean burn = (2.0 + 0.0) / 2 = 1.0
    # Expected log_gas for Jan = log1p(0.5), Feb = log1p(1.0)
    expected_log_gas_monthly = np.log1p(pd.Series([0.5, 1.0], index=df_monthly.index, name='log_gas'))
    assert_series_equal(df_monthly['log_gas'], expected_log_gas_monthly, check_dtype=False)

    # 6. Check that essential log columns exist after resampling and cleaning
    essential_log_cols = ["log_marketcap", "log_active", "log_gas", "log_nasdaq"]
    assert all(col in df_monthly.columns for col in essential_log_cols)

# (Test cases will be added here) 