# tests/test_diagnostics.py

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS, RegressionResultsWrapper
from unittest.mock import MagicMock, patch
from typing import Any, Dict

# Assuming src is importable via conftest.py
from src.diagnostics import run_residual_diagnostics, run_structural_break_tests

# --- Test Fixtures ---


@pytest.fixture
def sample_ols_data() -> Dict[str, Any]:
    """Provides basic data for fitting a real OLS model."""
    n_obs = 50
    # Use ME for MonthEnd frequency to avoid FutureWarning
    dates = pd.date_range(start="2020-01-01", periods=n_obs, freq="ME")
    X_data = pd.DataFrame(
        {
            "const": np.ones(n_obs),
            "x1": np.random.randn(n_obs) * 10,
            "x2": np.random.randn(n_obs) + 5,
        },
        index=dates,
    )
    y_data = 2 + 0.5 * X_data["x1"] - 1.5 * X_data["x2"] + np.random.randn(n_obs) * 2
    return {"y": y_data, "X": X_data}


@pytest.fixture
def fitted_ols_model(sample_ols_data: Dict[str, Any]) -> RegressionResultsWrapper:
    """Fits a real OLS model on sample data."""
    model = sm.OLS(sample_ols_data["y"], sample_ols_data["X"])
    return model.fit()


@pytest.fixture
def mock_ols_results_dict(fitted_ols_model: RegressionResultsWrapper) -> Dict[str, Any]:
    """Creates a results dictionary using a real fitted model."""
    fit = fitted_ols_model
    results_dict = {
        "model_obj": fit,
        "params": fit.params.to_dict(),
        "pvals_hac": fit.pvalues.to_dict(),  # Use non-HAC for mock simplicity
        "se_hac": fit.bse.to_dict(),  # Use non-HAC for mock simplicity
        "r2": fit.rsquared,
        "r2_adj": fit.rsquared_adj,
        "n_obs": int(fit.nobs),  # Ensure n_obs is int
        "resid": fit.resid,
        "fittedvalues": fit.fittedvalues,
        "model_formula": "y ~ const + x1 + x2",
        "error": None,
    }
    return results_dict


@pytest.fixture
def mock_break_dates() -> Dict[str, str]:
    return {"break1": "2020-06-30", "break2": "2021-01-31"}


# --- Helper Function to create Mock Fit Object ---
def create_mock_fit(
    n_obs: int, k_vars: int, index: pd.Index | pd.RangeIndex
) -> MagicMock:
    """Creates a MagicMock for RegressionResultsWrapper with necessary attributes."""
    mock_fit = MagicMock(spec=RegressionResultsWrapper)
    mock_fit.nobs = n_obs
    mock_fit.resid = pd.Series(np.random.randn(n_obs), index=index)

    # Mock the nested model structure properly
    mock_fit.model = MagicMock(spec=OLS)  # Mock the model attribute
    mock_fit.model.exog = np.random.randn(n_obs, k_vars)
    mock_fit.model.endog = np.random.randn(n_obs)

    # Mock the nested data structure
    mock_fit.model.data = MagicMock()  # Mock the data attribute
    mock_fit.model.data.row_labels = index  # Assign the index here

    return mock_fit


# --- Tests for run_residual_diagnostics ---


def test_residual_diagnostics_happy_path(mock_ols_results_dict: Dict[str, Any]):
    """Tests that residual diagnostics run and return expected keys."""
    # We need to patch acorr_breusch_godfrey because it requires the original OLS fit
    # and our mock dict provides a generic RegressionResultsWrapper potentially
    with patch(
        "src.diagnostics.acorr_breusch_godfrey", return_value=(1.0, 0.5, 1.0, 0.5)
    ):
        # Mock OLS fit inside run_residual_diagnostics for BG test refit
        with patch("src.diagnostics.sm.OLS") as mock_sm_ols:
            mock_sm_ols.return_value.fit.return_value = mock_ols_results_dict[
                "model_obj"
            ]
            results = run_residual_diagnostics(mock_ols_results_dict)

    assert isinstance(results, dict)
    expected_keys = ["DW", "BG_p", "BP_p", "White_p", "JB_p"]
    for key in expected_keys:
        assert key in results, (
            f"Expected key '{key}' not found in results: {results.keys()}"
        )
        # Check that values are floats or NaN (in case a test failed internally)
        assert isinstance(results[key], (float, np.floating)) or pd.isna(
            results[key]
        ), f"Value for '{key}' is not float or NaN: {results[key]}"

    # DW should be roughly between 0 and 4
    assert pd.isna(results["DW"]) or 0 <= results["DW"] <= 4
    # P-values should be between 0 and 1 or NaN
    assert pd.isna(results["BG_p"]) or 0 <= results["BG_p"] <= 1
    assert pd.isna(results["BP_p"]) or 0 <= results["BP_p"] <= 1
    assert pd.isna(results["White_p"]) or 0 <= results["White_p"] <= 1
    assert pd.isna(results["JB_p"]) or 0 <= results["JB_p"] <= 1


def test_residual_diagnostics_missing_model_obj():
    """Tests handling when the model object is missing."""
    results = run_residual_diagnostics({"error": "Some preceding error"})
    assert results == {}  # Should return empty dict


def test_residual_diagnostics_insufficient_residuals():
    """Tests handling when there are too few residuals."""
    # Create a mock specifically for this test
    n_obs_small = 3
    k_vars_small = 2
    index_small = pd.RangeIndex(n_obs_small)
    mock_fit_small = create_mock_fit(n_obs_small, k_vars_small, index_small)

    # Create the results dict using the small mock
    results_dict_small = {"model_obj": mock_fit_small, "n_obs": n_obs_small}

    results = run_residual_diagnostics(results_dict_small)
    assert results == {}  # Should return empty dict


# --- Tests for run_structural_break_tests ---


def test_structural_break_tests_happy_path(
    fitted_ols_model: RegressionResultsWrapper, mock_break_dates: Dict[str, str]
):
    """Tests structural break tests run with a real fit object."""
    # Use the real fitted model from the fixture
    results_dict = {"model_obj": fitted_ols_model}
    # Patch the plain OLS refit inside the CUSUM test
    with patch("src.diagnostics.sm.OLS") as mock_sm_ols:
        # Ensure the refit returns the same object for simplicity here
        mock_sm_ols.return_value.fit.return_value = fitted_ols_model
        results = run_structural_break_tests(results_dict, mock_break_dates)

    assert isinstance(results, dict)
    expected_keys = ["CUSUM_p", "Chow_break1_p", "Chow_break2_p"]
    print(f"Structural Break Test Results: {results}")  # Debug print
    for key in expected_keys:
        assert key in results, (
            f"Expected key '{key}' not found in results: {results.keys()}"
        )
        # Check that values are floats or NaN (in case a test failed internally)
        assert isinstance(results[key], (float, np.floating)) or pd.isna(
            results[key]
        ), f"Value for '{key}' is not float or NaN: {results[key]}"
        # P-values should be between 0 and 1 or NaN
        assert pd.isna(results[key]) or 0 <= results[key] <= 1, (
            f"P-value for '{key}' out of range: {results[key]}"
        )


def test_structural_break_tests_missing_model_obj(mock_break_dates: Dict[str, str]):
    """Tests handling when the model object is missing."""
    results = run_structural_break_tests(
        {"error": "Some preceding error"}, mock_break_dates
    )
    assert results == {}


def test_structural_break_tests_insufficient_data(mock_break_dates: Dict[str, str]):
    """Tests handling insufficient data for break tests."""
    n_obs_small = 10
    k_vars_small = 3  # const, x1, x2
    # Use ME for MonthEnd frequency
    dates_small = pd.date_range(start="2020-01-01", periods=n_obs_small, freq="ME")
    mock_fit_small = create_mock_fit(n_obs_small, k_vars_small, dates_small)

    results_dict_small = {"model_obj": mock_fit_small}

    results = run_structural_break_tests(results_dict_small, mock_break_dates)
    # Expect empty dict because it returns early due to insufficient obs
    assert results == {}


def test_structural_break_tests_invalid_break_date(
    fitted_ols_model: RegressionResultsWrapper,
):
    """Tests handling when a break date is outside the data range."""
    mock_break_dates = {"valid": "2020-06-30", "invalid": "2025-01-01"}
    results_dict = {"model_obj": fitted_ols_model}

    # Patch the plain OLS refit inside the CUSUM test
    with patch("src.diagnostics.sm.OLS") as mock_sm_ols:
        mock_sm_ols.return_value.fit.return_value = fitted_ols_model
        results = run_structural_break_tests(results_dict, mock_break_dates)

    assert "CUSUM_p" in results
    assert "Chow_valid_p" in results
    # Chow test for invalid date should calculate but result in NaN because insufficient data in post period
    assert pd.isna(results.get("Chow_invalid_p"))


def test_structural_break_tests_non_datetime_index(mock_break_dates: Dict[str, str]):
    """Tests handling when the model index is not a DatetimeIndex."""
    n_obs = 50
    k_vars = 3
    index_range = pd.RangeIndex(n_obs)
    mock_fit_range = create_mock_fit(n_obs, k_vars, index_range)
    results_dict = {"model_obj": mock_fit_range}

    # Patch the plain OLS refit inside the CUSUM test
    with patch("src.diagnostics.sm.OLS") as mock_sm_ols:
        # Create a mock fit object specifically for the OLS refit call
        mock_refit = create_mock_fit(n_obs, k_vars, index_range)
        mock_sm_ols.return_value.fit.return_value = mock_refit
        results = run_structural_break_tests(results_dict, mock_break_dates)

    assert "CUSUM_p" in results  # CUSUM should still run
    # Chow tests should fail gracefully and return NaN because index comparison fails
    assert pd.isna(results.get("Chow_break1_p"))
    assert pd.isna(results.get("Chow_break2_p"))
