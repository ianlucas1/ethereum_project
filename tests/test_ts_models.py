# tests/test_ts_models.py

import numpy as np
import pandas as pd
import pytest

# Assuming src is importable via conftest.py
from src.ts_models import (
    run_vecm_analysis,
)  # Add run_ardl_analysis later

# --- Fixtures ---


@pytest.fixture
def sample_coint_data() -> pd.DataFrame:
    """Generates synthetic cointegrated data (rank 1) for VECM tests."""
    np.random.seed(123)
    n_obs = 100
    dates = pd.date_range(start="2015-01-01", periods=n_obs, freq="ME")

    # I(1) series (random walk)
    x1 = np.random.randn(n_obs).cumsum() + 10

    # Second series cointegrated with x1: y = alpha + beta*x1 + error (I(0))
    alpha = 2.0
    beta = 0.75
    error = np.random.randn(n_obs) * 0.5  # Stationary error
    x2 = alpha + beta * x1 + error

    # Optional I(1) exogenous variable
    exog1 = np.random.rand(n_obs).cumsum() * 5 + 50

    df = pd.DataFrame(
        {
            "log_marketcap": x2,  # Treat as y1
            "log_active": x1,  # Treat as y2
            "nasdaq": exog1,  # Exogenous
        },
        index=dates,
    )
    return df


@pytest.fixture
def sample_non_coint_data() -> pd.DataFrame:
    """Generates synthetic non-cointegrated I(1) data."""
    np.random.seed(456)
    n_obs = 100
    dates = pd.date_range(start="2015-01-01", periods=n_obs, freq="ME")
    x1 = np.random.randn(n_obs).cumsum() + 20
    x2 = np.random.randn(n_obs).cumsum() + 50  # Independent random walk
    exog1 = np.random.rand(n_obs).cumsum() * 2 + 10
    df = pd.DataFrame(
        {"log_marketcap": x2, "log_active": x1, "nasdaq": exog1}, index=dates
    )
    return df


# --- Tests for run_vecm_analysis ---


def test_run_vecm_happy_path(sample_coint_data: pd.DataFrame):
    """Tests VECM analysis on cointegrated data."""
    df = sample_coint_data
    endog_cols = ["log_marketcap", "log_active"]
    exog_cols = ["nasdaq"]

    results = run_vecm_analysis(
        df_monthly=df,
        endog_cols=endog_cols,
        exog_cols=exog_cols,
        max_lags=4,
        coint_rank=1,  # Assume rank 1 for fitting
        det_order=0,  # Constant term
    )

    assert results["error"] is None
    assert isinstance(results.get("var_aic_lag"), (int, np.integer))
    assert isinstance(results.get("k_ar_diff"), (int, np.integer))
    assert isinstance(results.get("johansen_trace_stat"), list)
    assert isinstance(results.get("johansen_crit_5pct"), list)
    # Johansen test should suggest rank 1 for this data
    assert isinstance(results.get("johansen_suggested_rank"), (int, np.integer, str))
    assert results.get("johansen_suggested_rank") == 1
    assert isinstance(results.get("summary"), str)
    assert len(results["summary"]) > 0

    # Check extracted parameters (assuming rank 1)
    assert isinstance(results.get("coint_vector_norm"), list)
    assert len(results["coint_vector_norm"]) == 2  # [1.0, beta_norm]
    assert isinstance(results.get("beta_active_coint"), (float, np.floating))
    assert isinstance(results.get("alpha_coeffs"), list)
    assert len(results["alpha_coeffs"]) == 2  # One alpha for each endog var
    assert isinstance(results.get("alpha_pvals"), list)
    assert len(results["alpha_pvals"]) == 2
    assert isinstance(results.get("alpha_mcap"), (float, np.floating))
    assert isinstance(results.get("alpha_mcap_p"), (float, np.floating))
    assert isinstance(results.get("alpha_active_p"), (float, np.floating))

    # Expect alpha_mcap to be negative (error correction) and significant
    assert results.get("alpha_mcap") < 0
    assert (
        results.get("alpha_mcap_p") < 0.10
    )  # Use slightly relaxed p-value for synthetic data


def test_run_vecm_non_coint_data(sample_non_coint_data: pd.DataFrame):
    """Tests VECM analysis on non-cointegrated data."""
    df = sample_non_coint_data
    endog_cols = ["log_marketcap", "log_active"]
    exog_cols = ["nasdaq"]

    results = run_vecm_analysis(
        df_monthly=df,
        endog_cols=endog_cols,
        exog_cols=exog_cols,
        max_lags=4,
        coint_rank=1,  # Still fit with rank 1, but Johansen should differ
        det_order=0,
    )

    assert results["error"] is None
    # Johansen test should suggest rank 0 for this data
    assert results.get("johansen_suggested_rank") == 0
    assert isinstance(results.get("summary"), str)  # Fit should still run

    # Parameters might be extracted but less meaningful
    assert isinstance(results.get("coint_vector_norm"), list)
    assert isinstance(results.get("alpha_coeffs"), list)


def test_run_vecm_missing_columns(sample_coint_data: pd.DataFrame):
    """Tests VECM error handling for missing columns."""
    df = sample_coint_data.drop(columns=["nasdaq"])  # Drop exogenous
    endog_cols = ["log_marketcap", "log_active"]
    exog_cols = ["nasdaq"]  # Still require nasdaq

    results = run_vecm_analysis(
        df_monthly=df,
        endog_cols=endog_cols,
        exog_cols=exog_cols,
    )

    assert results["error"] is not None
    # Check if the expected start is IN the error message
    assert "Monthly DataFrame missing required columns" in results["error"]


def test_run_vecm_insufficient_data(sample_coint_data: pd.DataFrame):
    """Tests VECM error handling for insufficient data."""
    df = sample_coint_data.iloc[:10]  # Only 10 observations
    endog_cols = ["log_marketcap", "log_active"]
    exog_cols = ["nasdaq"]

    results = run_vecm_analysis(
        df_monthly=df, endog_cols=endog_cols, exog_cols=exog_cols, max_lags=4
    )

    assert results["error"] is not None
    assert "Insufficient observations" in results["error"]


# --- Tests for run_ardl_analysis (To be added later) ---
