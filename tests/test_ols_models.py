# tests/test_ols_models.py

import numpy as np
import pandas as pd
import pytest
from statsmodels.regression.linear_model import OLSResults
from typing import Any, Dict

# Assuming src is importable via conftest.py
from src.ols_models import fit_ols_hac

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

    assert error_occurred or condition_number_high, (
        f"Expected an error or high condition number due to collinearity, but got error='{results.get('error')}' and cond_num='{cond_num}'"
    )

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
