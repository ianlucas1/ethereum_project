# tests/test_walk_forward.py

import pandas as pd
import numpy as np
import pytest

# Assuming src is importable via conftest.py
from src.validation import run_oos_validation

# --- Test Data ---

@pytest.fixture
def sample_time_series_df() -> pd.DataFrame:
    """Provides a simple DataFrame with a time index for splitting tests."""
    n_obs = 30 # Enough for a few splits
    dates = pd.date_range(start='2023-01-01', periods=n_obs, freq='ME')
    # Add dummy data, columns needed by run_oos_validation signature
    data = {
        'target': np.random.randn(n_obs),
        'feature1': np.random.randn(n_obs),
        'feature2': np.random.randn(n_obs),
        'to_winsorize': np.random.randn(n_obs),
        'to_stationarity_test': np.random.randn(n_obs),
        'price_usd': np.random.rand(n_obs) * 1000, # Add columns needed by reporting/downstream
        'supply': np.random.rand(n_obs) * 1e6,
    }
    return pd.DataFrame(data, index=dates)

# --- Test Cases ---

# (Test cases will be added here)
def test_run_oos_validation_splitting(sample_time_series_df):
    """
    Tests the walk-forward splitting logic within run_oos_validation.
    Checks number of splits, window sizes, and non-overlapping nature.
    """
    df = sample_time_series_df
    n_obs = len(df)
    test_window_size = 24 # Example window size

    # Define minimal arguments needed to run the function
    endog_col = 'target'
    exog_cols = ['feature1', 'feature2']
    # Provide empty lists for preprocessing steps if not testing them here
    winsorize_cols = []
    stationarity_cols = []

    # Run the validation function
    results = run_oos_validation(
        df_monthly=df,
        endog_col=endog_col,
        exog_cols=exog_cols,
        winsorize_cols=winsorize_cols,
        winsorize_quantile=0.99, # Value doesn't matter if cols list is empty
        stationarity_cols=stationarity_cols,
        window_size=test_window_size
    )

    # --- Assertions ---
    # 1. Check number of predictions/splits
    expected_n_predictions = n_obs - test_window_size
    assert len(results["predictions"]) == expected_n_predictions, \
        f"Expected {expected_n_predictions} predictions, but got {len(results['predictions'])}"
    assert len(results["actuals"]) == expected_n_predictions
    assert len(results["residuals"]) == expected_n_predictions
    assert len(results["train_indices"]) == expected_n_predictions
    assert len(results["test_indices"]) == expected_n_predictions

    # 2. Check window sizes and non-overlap for each split
    for i in range(expected_n_predictions):
        train_idx = results["train_indices"][i]
        test_idx = results["test_indices"][i]

        # a) Check training window size
        assert len(train_idx) == test_window_size, \
            f"Split {i}: Expected train size {test_window_size}, got {len(train_idx)}"

        # b) Check test window size (should be 1)
        assert len(test_idx) == 1, \
            f"Split {i}: Expected test size 1, got {len(test_idx)}"

        # c) Check non-overlap and correct progression
        # The test index should be the one immediately following the last training index
        expected_test_date = train_idx[-1] + pd.DateOffset(months=1)
        # Ensure the test date is aligned to month end if original index was month end
        expected_test_date = expected_test_date + pd.offsets.MonthEnd(0)

        assert test_idx[0] == expected_test_date, \
             f"Split {i}: Test index {test_idx[0]} doesn't immediately follow train index end {train_idx[-1]} + 1 month offset ({expected_test_date})"

        # d) Check start of training window progression
        expected_train_start_index = i # Corresponds to df.iloc[i]
        assert train_idx[0] == df.index[expected_train_start_index], \
            f"Split {i}: Expected train start index {expected_train_start_index} ({df.index[expected_train_start_index]}), got {train_idx[0]}" 