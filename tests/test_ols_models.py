# tests/test_ols_models.py

from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from statsmodels.regression.linear_model import OLSResults

# Assuming src is importable via conftest.py
from src.ols_models import fit_ols_hac, run_ols_benchmarks

# --- Fixtures ---


@pytest.fixture
def sample_ols_data() -> Dict[str, pd.DataFrame | pd.Series]:
    """Provides sample data suitable for OLS fitting."""
    n_obs = 50
    dates = pd.date_range(start="2020-01-01", periods=n_obs, freq="ME")
    X_data = pd.DataFrame(
        {"x1": np.random.randn(n_obs) * 10 + 5, "x2": np.random.randn(n_obs) + 2},
        index=dates,
    )
    # Introduce some NaNs
    X_data.iloc[5, 0] = np.nan
    X_data.iloc[10, 1] = np.nan

    y_data = 2 + 0.5 * X_data["x1"] - 1.5 * X_data["x2"] + np.random.randn(n_obs) * 2
    y_data.iloc[15] = np.nan  # NaN in y

    return {"y": y_data, "X": X_data}


# --- Tests for fit_ols_hac ---


def test_fit_ols_hac_happy_path(sample_ols_data: Dict[str, Any]):
    """Tests basic OLS fitting with HAC errors."""
    y = sample_ols_data["y"]
    X = sample_ols_data["X"]
    results = fit_ols_hac(
        y=y, X=X, add_const=True, lags=4
    )  # Use fewer lags for test speed

    assert results["error"] is None
    assert isinstance(results["model_obj"], OLSResults)
    assert "const" in results["params"]
    assert "x1" in results["params"]
    assert "x2" in results["params"]
    assert "const" in results["pvals_hac"]
    assert "x1" in results["pvals_hac"]
    assert "x2" in results["pvals_hac"]
    assert "const" in results["se_hac"]
    assert "x1" in results["se_hac"]
    assert "x2" in results["se_hac"]
    assert isinstance(results["r2"], float) and not np.isnan(results["r2"])
    assert isinstance(results["r2_adj"], float) and not np.isnan(results["r2_adj"])
    assert results["n_obs"] == 47  # 50 initial - 3 NaNs
    assert isinstance(results["resid"], pd.Series)
    assert isinstance(results["fittedvalues"], pd.Series)
    assert len(results["resid"]) == results["n_obs"]
    assert len(results["fittedvalues"]) == results["n_obs"]
    assert "y ~ const + x1 + x2 (HAC lags=4)" in results["model_formula"]


def test_fit_ols_hac_no_const(sample_ols_data: Dict[str, Any]):
    """Tests fitting without adding a constant."""
    y = sample_ols_data["y"]
    X = sample_ols_data["X"]
    results = fit_ols_hac(y=y, X=X, add_const=False, lags=4)

    assert results["error"] is None
    assert "const" not in results["params"]
    assert "x1" in results["params"]
    assert "x2" in results["params"]
    assert "y ~ x1 + x2 (HAC lags=4)" in results["model_formula"]
    assert results["n_obs"] == 47


def test_fit_ols_hac_insufficient_data(sample_ols_data: Dict[str, Any]):
    """Tests handling when too few observations remain after dropping NaNs."""
    # k_regressors = 2 (x1, x2) + 1 (const) = 3
    # We need len(df_fit) < min_obs_needed (which is k+2 = 5)
    # Let's ensure len(df_fit) is <= k_regressors (i.e., <= 3)
    y = sample_ols_data["y"].iloc[:3]  # Take only first 3 rows
    X = sample_ols_data["X"].iloc[:3]  # No NaNs in first 3 rows here
    # Now len(df_fit) will be 3, which is < min_obs_needed (5)
    results = fit_ols_hac(y=y, X=X, add_const=True, lags=1)

    assert results["error"] == "Insufficient observations."
    assert results["model_obj"] is None
    # CORRECTED: n_obs should be 0 when error occurs before fit
    assert results["n_obs"] == 0
    assert np.isnan(results["r2"])


def test_fit_ols_hac_perfect_collinearity(sample_ols_data: Dict[str, Any]):
    """Tests handling of perfect collinearity."""
    y = sample_ols_data["y"]
    X = sample_ols_data["X"].copy()
    X["x3"] = X["x1"] * 2  # Add perfectly collinear column

    results = fit_ols_hac(y=y, X=X, add_const=True, lags=4)

    # Check if an error was explicitly caught OR if the model fit indicates collinearity
    error_occurred = results["error"] is not None and (
        "Singular matrix" in results["error"] or "collinear" in results["error"].lower()
    )

    condition_number_high = False
    cond_num = (
        "N/A"  # Initialize cond_num to avoid potential reference before assignment
    )
    if results["model_obj"] is not None:
        try:
            # Check condition number if model object exists
            cond_num = getattr(results["model_obj"], "condition_number", None)
            if cond_num is not None and cond_num > 1e8:  # Use a large threshold
                condition_number_high = True
        except Exception:
            pass  # Ignore errors trying to get condition number

    assert (
        error_occurred or condition_number_high
    ), f"Expected an error or high condition number due to collinearity, but got error='{results.get('error')}' and cond_num='{cond_num}'"

    # If an error occurred, model_obj should be None and r2 NaN
    if error_occurred:
        assert results["model_obj"] is None
        assert np.isnan(results["r2"])
    # If no error but high condition number, model might exist but results are unreliable
    elif condition_number_high:
        assert results["model_obj"] is not None  # Model might exist
        # Don't assert on r2 as it might be calculated but meaningless
    else:
        # This case should fail the main assertion above
        pass


def test_fit_ols_hac_input_types(sample_ols_data: Dict[str, Any]):
    """Tests error handling for incorrect input types."""
    y_list = sample_ols_data["y"].tolist()
    X_df = sample_ols_data["X"]
    y_series = sample_ols_data["y"]
    X_np = sample_ols_data["X"].values

    results_bad_y = fit_ols_hac(y=y_list, X=X_df)  # y is list
    assert results_bad_y["error"] == "Incorrect input types."

    results_bad_X = fit_ols_hac(y=y_series, X=X_np)  # X is numpy array
    assert results_bad_X["error"] == "Incorrect input types."


def test_fit_ols_hac_unnamed_series(sample_ols_data: Dict[str, Any]):
    """Tests handling when input Series has no name."""
    y = sample_ols_data["y"].copy()
    y.name = None  # Remove name
    X = sample_ols_data["X"]
    results = fit_ols_hac(y=y, X=X, add_const=True, lags=4)

    assert results["error"] is None
    assert (
        "y ~ const + x1 + x2 (HAC lags=4)" in results["model_formula"]
    )  # Uses default 'y'


# --- Fixture for run_ols_benchmarks ---


@pytest.fixture
def sample_benchmark_data() -> Dict[str, pd.DataFrame]:
    """Provides sample monthly data for OLS benchmark tests."""
    n_obs = 60  # 5 years of monthly data
    dates = pd.date_range(start="2019-01-01", periods=n_obs, freq="ME")

    # Simulate log-scale data with plausible relationships
    log_active = np.linspace(10, 15, n_obs) + np.random.randn(n_obs) * 0.2
    log_nasdaq = np.linspace(8, 9.5, n_obs) + np.random.randn(n_obs) * 0.1
    log_gas = np.linspace(1, 3, n_obs) + np.random.randn(n_obs) * 0.3
    # Simulate log_marketcap based on others + noise
    log_marketcap = (
        -5  # Intercept
        + 1.5 * log_active  # Base relationship
        + 0.5 * log_nasdaq  # Macro effect
        + 0.2 * log_gas  # Gas effect
        + np.random.randn(n_obs) * 0.5  # Noise
    )

    # Back out price and supply (approximate)
    supply = np.linspace(100e6, 120e6, n_obs)
    market_cap = np.exp(log_marketcap)
    price_usd = market_cap / supply

    df = pd.DataFrame(
        {
            "log_marketcap": log_marketcap,
            "log_active": log_active,
            "log_nasdaq": log_nasdaq,
            "log_gas": log_gas,
            "price_usd": price_usd,
            "supply": supply,
            # Add other columns that might exist but aren't used directly here
            "active_addr": np.exp(log_active),
            "nasdaq": np.exp(log_nasdaq),
            "burn": np.expm1(log_gas),  # approx inverse of log1p
        },
        index=dates,
    )

    # Introduce a few NaNs to test robustness
    df.loc[df.index[5], "log_nasdaq"] = np.nan
    df.loc[df.index[10], "log_gas"] = np.nan
    df.loc[df.index[15], "log_marketcap"] = np.nan

    # Pass back a dictionary containing the df (and an unused daily_df placeholder)
    return {"monthly": df.copy(), "daily": pd.DataFrame()}  # Pass copy


# --- Tests for run_ols_benchmarks ---


def test_run_ols_benchmarks_structure_and_keys(
    sample_benchmark_data: Dict[str, pd.DataFrame],
):
    """Tests the basic structure and keys returned by run_ols_benchmarks."""
    monthly_df = sample_benchmark_data["monthly"]
    daily_df = sample_benchmark_data["daily"]  # Unused placeholder
    original_cols = monthly_df.columns.tolist()

    results = run_ols_benchmarks(daily_df=daily_df, monthly_df=monthly_df)

    assert isinstance(results, dict)
    assert "monthly_base" in results
    assert "monthly_extended" in results
    assert "monthly_constrained" in results
    assert "error" not in results  # Should not have top-level error

    # Check structure of sub-dictionaries (expecting fit_ols_hac structure + RMSE)
    for key in ["monthly_base", "monthly_extended"]:
        assert isinstance(results[key], dict)
        assert "params" in results[key]
        assert "pvals_hac" in results[key]
        assert "r2" in results[key]
        assert "RMSE_USD" in results[key]  # Check RMSE was added
        assert results[key].get("error") is None  # Check no error within sub-model

    assert isinstance(results["monthly_constrained"], dict)
    assert "RMSE_USD" in results["monthly_constrained"]

    # Check that fair value columns were added to the input DataFrame
    assert "fair_price_base" in monthly_df.columns
    assert "fair_price_ext" in monthly_df.columns
    assert "fair_price_constr" in monthly_df.columns
    # Ensure no other columns were unexpectedly added/removed
    assert set(monthly_df.columns) == set(
        original_cols + ["fair_price_base", "fair_price_ext", "fair_price_constr"]
    )


def test_run_ols_benchmarks_calculations(
    sample_benchmark_data: Dict[str, pd.DataFrame],
):
    """Tests the fair value and RMSE calculations."""
    monthly_df = sample_benchmark_data["monthly"]
    daily_df = sample_benchmark_data["daily"]

    results = run_ols_benchmarks(daily_df=daily_df, monthly_df=monthly_df)

    # --- Check Base Model ---
    base_results = results["monthly_base"]
    assert base_results["error"] is None
    assert isinstance(base_results.get("RMSE_USD"), (float, np.floating))
    assert pd.notna(base_results["RMSE_USD"])
    assert "fair_price_base" in monthly_df.columns
    assert monthly_df["fair_price_base"].isna().sum() < len(
        monthly_df
    )  # Should have calculated some values

    # Check if calculated fair value seems reasonable (e.g., positive)
    assert (monthly_df["fair_price_base"].dropna() > 0).all()

    # --- Check Extended Model ---
    ext_results = results["monthly_extended"]
    assert ext_results["error"] is None
    assert isinstance(ext_results.get("RMSE_USD"), (float, np.floating))
    assert pd.notna(ext_results["RMSE_USD"])
    assert "fair_price_ext" in monthly_df.columns
    assert monthly_df["fair_price_ext"].isna().sum() < len(monthly_df)
    assert (monthly_df["fair_price_ext"].dropna() > 0).all()

    # --- Check Constrained Model ---
    constr_results = results["monthly_constrained"]
    assert isinstance(constr_results.get("RMSE_USD"), (float, np.floating))
    assert pd.notna(constr_results["RMSE_USD"])
    assert "fair_price_constr" in monthly_df.columns
    assert monthly_df["fair_price_constr"].isna().sum() < len(monthly_df)
    assert (monthly_df["fair_price_constr"].dropna() > 0).all()


def test_run_ols_benchmarks_missing_columns(
    sample_benchmark_data: Dict[str, pd.DataFrame],
):
    """Tests behavior when required columns are missing."""
    monthly_df = sample_benchmark_data["monthly"].drop(columns=["log_nasdaq", "supply"])
    daily_df = sample_benchmark_data["daily"]

    results = run_ols_benchmarks(daily_df=daily_df, monthly_df=monthly_df)

    assert "error" in results
    assert "Missing required monthly columns" in results["error"]
    # Check that sub-results are empty or indicate failure
    assert not results.get("monthly_base")  # Should be empty dict
    assert not results.get("monthly_extended")
    assert not results.get("monthly_constrained")
