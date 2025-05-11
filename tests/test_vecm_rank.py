# tests/test_vecm_rank.py

import numpy as np
import pandas as pd
import pytest

# Assuming src is importable via conftest.py
from src.ts_models import run_vecm_analysis

# --- Test Data ---


@pytest.fixture
def synthetic_coint_data() -> pd.DataFrame:
    """Generates synthetic cointegrated data with rank 1."""
    np.random.seed(42)
    n_obs = 200
    dates = pd.date_range(start="2000-01-01", periods=n_obs, freq="ME")

    # Generate a random walk (I(1))
    rw = np.random.randn(n_obs).cumsum()

    # Generate a cointegrated series: y = alpha + beta*rw + error (I(0))
    alpha = 5.0
    beta = 2.0
    stationary_noise = np.random.randn(n_obs) * 0.5  # I(0) noise
    coint_series = alpha + beta * rw + stationary_noise

    # Combine into DataFrame
    df = pd.DataFrame({"random_walk": rw, "coint_variable": coint_series}, index=dates)
    return df


# --- Test Cases ---


# (Test cases will be added here)
def test_vecm_rank_detection(synthetic_coint_data):
    """
    Tests if run_vecm_analysis (via Johansen test) correctly identifies
    the cointegration rank of the synthetic data as 1.
    """
    df = synthetic_coint_data
    endog_cols = ["random_walk", "coint_variable"]
    test_max_lags = 4
    test_det_order = 0

    # Run the VECM analysis function
    vecm_results = run_vecm_analysis(
        df_monthly=df,
        endog_cols=endog_cols,
        exog_cols=None,
        max_lags=test_max_lags,
        coint_rank=1,  # Assumed rank for VECM fit itself
        det_order=test_det_order,
    )

    # Assert that the Johansen test suggested rank is 1
    assert "johansen_suggested_rank" in vecm_results, "Johansen rank result missing."
    assert (
        vecm_results["johansen_suggested_rank"] == 1
    ), f"Expected Johansen rank 1, but got {vecm_results['johansen_suggested_rank']}"

    # Optional: Check if trace stats and critical values seem reasonable
    assert "johansen_trace_stat" in vecm_results
    assert "johansen_crit_5pct" in vecm_results
    assert (
        len(vecm_results["johansen_trace_stat"]) == 2
    )  # Should have 2 stats for 2 variables
    assert len(vecm_results["johansen_crit_5pct"]) == 2
    # Expect trace stat for r=0 to be > crit (reject r=0)
    assert (
        vecm_results["johansen_trace_stat"][0] > vecm_results["johansen_crit_5pct"][0]
    )
    # Expect trace stat for r=1 to be < crit (fail to reject r=1)
    assert (
        vecm_results["johansen_trace_stat"][1] < vecm_results["johansen_crit_5pct"][1]
    )
