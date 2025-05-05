# tests/test_validation.py

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm  # Needed for mocking OLS
from unittest.mock import patch, MagicMock

# Assuming src is importable via conftest.py
from src.validation import run_oos_validation

# --- Fixtures ---


@pytest.fixture
def sample_oos_data() -> pd.DataFrame:
    """Provides sample monthly data suitable for OOS validation."""
    n_obs = 30  # Enough for a few OOS steps
    dates = pd.date_range(start="2020-01-01", periods=n_obs, freq="ME")
    df = pd.DataFrame(
        {
            "target_log": np.linspace(10, 15, n_obs) + np.random.randn(n_obs) * 0.1,
            "feature1": np.linspace(5, 8, n_obs) + np.random.randn(n_obs) * 0.2,
            "feature2": np.random.randn(n_obs).cumsum() + 50,
            "winsor_col": np.random.rand(n_obs) * 100,
            "stationarity_col": np.random.randn(n_obs).cumsum(),
            # Add price/supply needed by internal OLS/reporting mocks if we tested deeper
            "price_usd": np.exp(np.linspace(7, 8, n_obs)),
            "supply": np.linspace(1e8, 1.1e8, n_obs),
        },
        index=dates,
    )
    # Add some NaNs to test handling within windows
    df.loc[df.index[3], "feature1"] = np.nan
    df.loc[df.index[8], "target_log"] = np.nan
    return df


# --- Tests for run_oos_validation ---


@patch("src.validation.winsorize_data")
@patch("src.validation.run_stationarity_tests")
@patch("src.validation.sm.OLS")  # Mock statsmodels OLS directly
def test_run_oos_validation_happy_path(
    mock_ols: MagicMock,
    mock_run_stationarity: MagicMock,
    mock_winsorize: MagicMock,
    sample_oos_data: pd.DataFrame,
):
    """Tests the OOS validation loop, mocking sub-functions."""
    df = sample_oos_data
    window_size = 24
    n_obs = len(df)
    expected_oos_predictions = n_obs - window_size

    # --- Mock Setup ---
    mock_winsorize.side_effect = lambda df, **kwargs: df.copy()
    mock_run_stationarity.return_value = pd.DataFrame(
        {"series": [], "ADF p": [], "KPSS p": []}
    )

    # --- Simpler Mock OLS ---
    mock_fitted_model = MagicMock(
        spec=sm.regression.linear_model.RegressionResultsWrapper,
        predict=MagicMock(),  # Add predict attribute explicitly
    )
    # Define expected exog names for a successful fit (including const)
    expected_exog_names = ["const", "feature1", "feature2"]
    mock_fitted_model.params = pd.Series(
        index=expected_exog_names, data=np.random.rand(len(expected_exog_names))
    )
    # Mock the model attribute and its exog_names
    mock_fitted_model.model = MagicMock()
    mock_fitted_model.model.exog_names = expected_exog_names
    # Add dummy resid/fittedvalues attributes
    mock_fitted_model.resid = pd.Series(dtype=float)
    mock_fitted_model.fittedvalues = pd.Series(dtype=float)

    def mock_predict(X_test_ordered):
        # X_test_ordered should have columns matching expected_exog_names
        # if the main code logic worked correctly before calling predict.
        if X_test_ordered.empty or not all(
            c in X_test_ordered for c in expected_exog_names
        ):
            return pd.Series(
                [np.nan] * len(X_test_ordered) if not X_test_ordered.empty else [np.nan]
            )

        const_col = "const"
        feature_col = "feature1"
        # Handle potential NaN in test feature
        if X_test_ordered[feature_col].isnull().any():
            return pd.Series([np.nan] * len(X_test_ordered))

        # Dummy prediction logic
        preds = X_test_ordered[const_col] * 0.1 + X_test_ordered[feature_col] * 0.5 + 5
        return pd.Series(preds.values, index=X_test_ordered.index)

    mock_fitted_model.predict.side_effect = mock_predict

    # Mock the fit method of the OLS instance to return our mock_fitted_model
    # This assumes OLS(y, X) is called, and then .fit()
    mock_ols.return_value.fit.return_value = mock_fitted_model
    # --- End Mock Setup ---

    # Add the NaN later in the test data again to test NaN prediction
    df.loc[df.index[25], "feature1"] = np.nan

    results = run_oos_validation(
        df_monthly=df,
        endog_col="target_log",
        exog_cols=["feature1", "feature2"],
        winsorize_cols=["winsor_col"],
        winsorize_quantile=0.99,
        stationarity_cols=["stationarity_col"],
        window_size=window_size,
        add_const=True,
    )

    # --- Assertions ---
    assert isinstance(results, dict)
    # We expect 6 prediction attempts.
    # OLS fit itself should succeed (as mocked).
    # Prediction fails for step i=25 because test X has NaN.
    # So N_OOS should be 5.
    assert results["N_OOS"] == expected_oos_predictions - 1, (
        f"Expected N_OOS={expected_oos_predictions - 1}, Got={results['N_OOS']}"
    )
    assert len(results["predictions"]) == expected_oos_predictions
    assert len(results["actuals"]) == expected_oos_predictions
    assert len(results["residuals"]) == expected_oos_predictions
    assert (
        len(results["models"]) == expected_oos_predictions
    )  # Should store the mock model object
    assert len(results["train_indices"]) == expected_oos_predictions
    assert len(results["test_indices"]) == expected_oos_predictions

    # Check metrics were calculated
    assert "oos_rmse" in results
    assert "oos_mae" in results
    assert "oos_directional_accuracy" in results
    if results["N_OOS"] > 1:
        assert pd.notna(results["oos_rmse"])
        assert pd.notna(results["oos_mae"])
    else:
        assert pd.isna(results["oos_rmse"]) or pd.notna(results["oos_rmse"])

    # Check predictions_df
    assert isinstance(results["predictions_df"], pd.DataFrame)
    assert not results["predictions_df"].empty
    assert results["predictions_df"].shape[0] == expected_oos_predictions
    assert results["predictions_df"].index.equals(df.index[window_size:])
    assert results["predictions_df"].columns == ["predicted_price_oos"]
    # Check the NaN prediction at index 25 (iloc 1)
    assert pd.isna(results["predictions"][1])
    assert pd.isna(results["predictions_df"]["predicted_price_oos"].iloc[1])

    # Check mocks were called correctly
    assert mock_winsorize.call_count == expected_oos_predictions
    assert mock_run_stationarity.call_count == expected_oos_predictions
    # Check OLS fit mock call count matches number of prediction attempts
    assert mock_ols.return_value.fit.call_count == expected_oos_predictions


def test_run_oos_validation_insufficient_data(sample_oos_data: pd.DataFrame):
    """Tests behavior when input data is too short for even one window."""
    window_size = 24
    df = sample_oos_data.iloc[:window_size]  # Exactly window_size observations

    results = run_oos_validation(
        df_monthly=df,
        endog_col="target_log",
        exog_cols=["feature1", "feature2"],
        winsorize_cols=["winsor_col"],
        winsorize_quantile=0.99,
        stationarity_cols=["stationarity_col"],
        window_size=window_size,
        add_const=True,
    )

    # Expect empty/default results
    assert results["N_OOS"] == 0
    assert len(results["predictions"]) == 0
    assert len(results["actuals"]) == 0
    assert pd.isna(results["oos_rmse"])
    assert pd.isna(results["oos_mae"])
    assert pd.isna(results["oos_directional_accuracy"])
    assert results["predictions_df"].empty
