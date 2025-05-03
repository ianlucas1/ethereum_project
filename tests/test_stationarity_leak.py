# tests/test_stationarity_leak.py

import pandas as pd
import numpy as np

# Assuming src is importable due to conftest.py or PYTHONPATH setup
from src.eda import run_stationarity_tests


def test_stationarity_test_windowing():
    """
    Tests that run_stationarity_tests uses the window_mask correctly
    to test only the specified subset of data.
    """
    # 1. Create toy data: first half non-stationary (random walk), second half stationary (mean reverting)
    n_total = 100
    n_half = n_total // 2
    dates = pd.date_range(start="2023-01-01", periods=n_total, freq="D")

    # Non-stationary part (random walk)
    np.random.seed(42)
    rw_part = np.random.randn(n_half).cumsum() + 100

    # Stationary part (mean reverting noise around a constant)
    stationary_part = 50 + np.random.randn(n_half) * 5

    # Combine
    data = {"value": np.concatenate([rw_part, stationary_part])}
    df = pd.DataFrame(data, index=dates)

    cols_to_test = ["value"]

    # 2. Define masks for each half
    first_half_mask = df.index < dates[n_half]
    second_half_mask = df.index >= dates[n_half]

    # --- Assertions ---

    # 3. Test first half (expect non-stationary -> high ADF p-value)
    results_first_half_df = run_stationarity_tests(
        df=df, cols_to_test=cols_to_test, window_mask=first_half_mask
    )
    # Extract ADF p-value for 'value' column
    adf_p_first_half_str = results_first_half_df.set_index("series").loc[
        "value", "ADF p"
    ]
    assert adf_p_first_half_str != "N/A", "ADF test failed for first half"
    adf_p_first_half = float(adf_p_first_half_str)
    print(f"\nADF p-value (First Half - Random Walk): {adf_p_first_half:.4f}")
    assert adf_p_first_half > 0.05, (
        f"First half (random walk) should be non-stationary (ADF p > 0.05), but got p={adf_p_first_half:.4f}"
    )

    # 4. Test second half (expect stationary -> low ADF p-value)
    results_second_half_df = run_stationarity_tests(
        df=df, cols_to_test=cols_to_test, window_mask=second_half_mask
    )
    adf_p_second_half_str = results_second_half_df.set_index("series").loc[
        "value", "ADF p"
    ]
    assert adf_p_second_half_str != "N/A", "ADF test failed for second half"
    adf_p_second_half = float(adf_p_second_half_str)
    print(f"ADF p-value (Second Half - Stationary): {adf_p_second_half:.4f}")
    assert adf_p_second_half < 0.05, (
        f"Second half (stationary) should be stationary (ADF p < 0.05), but got p={adf_p_second_half:.4f}"
    )

    # 5. Test full series (expect non-stationary overall)
    results_full_df = run_stationarity_tests(
        df=df,
        cols_to_test=cols_to_test,
        window_mask=None,  # No mask
    )
    adf_p_full_str = results_full_df.set_index("series").loc["value", "ADF p"]
    assert adf_p_full_str != "N/A", "ADF test failed for full series"
    adf_p_full = float(adf_p_full_str)
    print(f"ADF p-value (Full Series): {adf_p_full:.4f}")
    # Depending on the mix, the full series is usually non-stationary
    assert adf_p_full > 0.05, (
        f"Full series should likely be non-stationary (ADF p > 0.05), but got p={adf_p_full:.4f}"
    )
