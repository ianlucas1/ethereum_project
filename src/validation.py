# src/validation.py
import logging
from typing import Any, Dict

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.eda import run_stationarity_tests, winsorize_data

# --- Out-of-Sample Rolling Validation --------------------------------------------------


def run_oos_validation(
    df_monthly: pd.DataFrame,
    endog_col: str,
    exog_cols: list[str],
    winsorize_cols: list[str],
    winsorize_quantile: float,
    stationarity_cols: list[str],
    window_size: int = 24,
    add_const: bool = True,
) -> Dict[str, Any]:  # ←── parameterised Dict fixes mypy complaint
    """
    Performs rolling out-of-sample (OOS) validation for an OLS model.

    Args:
        df_monthly: Monthly DataFrame with features and target.
        endog_col: Name of the endogenous (target) variable column.
        exog_cols: List of exogenous (feature) variable column names.
        winsorize_cols: List of columns to winsorize within each training window.
        winsorize_quantile: The quantile to use for winsorizing.
        stationarity_cols: List of columns to test for stationarity within each training window.
        window_size: The size of the rolling window (in months).
        add_const: Whether to add a constant to the exogenous variables.

    Returns:
        Dict with OOS predictions, actuals, residuals, fitted models, indices, and metrics.
    """
    logging.info(
        f"Starting OOS validation for '{endog_col}' ~ {' + '.join(exog_cols)} "
        f"with window size {window_size}."
    )

    results: Dict[str, Any] = {
        "predictions": [],
        "actuals": [],
        "residuals": [],
        "models": [],  # Store fitted model objects if needed later
        "train_indices": [],
        "test_indices": [],
    }

    n_obs = len(df_monthly)

    # Check if enough data for at least one window + 1 prediction
    if n_obs < window_size + 1:
        logging.error(
            f"Insufficient data ({n_obs} obs) for OOS validation with window size "
            f"{window_size}. Need at least {window_size + 1}."
        )
        return results  # Return empty results

    for i in range(window_size, n_obs):
        train_data = df_monthly.iloc[i - window_size : i]
        test_data_point = df_monthly.iloc[[i]]  # Select the single row for prediction

        # Winsorize the training data for this window only
        train_data_winsorized = winsorize_data(
            df=train_data,
            cols_to_cap=winsorize_cols,
            quantile=winsorize_quantile,
            window_mask=train_data.index,
        )

        # Run stationarity tests on the winsorized training data for this window
        if stationarity_cols:
            window_end_date = train_data.index[-1].date()
            logging.debug(
                "Running stationarity tests for OOS window ending %s", window_end_date
            )
            stationarity_results_window = run_stationarity_tests(
                df=train_data_winsorized,
                cols_to_test=stationarity_cols,
                window_mask=None,
            )
            logging.debug(
                "Stationarity Results (Window %s):\n%s",
                window_end_date,
                stationarity_results_window.to_string(),
            )

        # Prepare training and test sets
        y_train = train_data_winsorized[endog_col]
        X_train = train_data_winsorized[exog_cols]
        X_test = test_data_point[exog_cols]

        if add_const:
            X_train = sm.add_constant(X_train, has_constant="add")
            X_test = sm.add_constant(X_test, has_constant="add")

        # Skip window if NaNs remain
        if X_train.isnull().any().any() or y_train.isnull().any():
            logging.warning(
                "NaNs found in training data for window ending at index %d. "
                "Skipping this window.",
                i,
            )
            results["predictions"].append(np.nan)
            results["actuals"].append(test_data_point[endog_col].iloc[0])
            results["residuals"].append(np.nan)
            results["models"].append(None)
            results["train_indices"].append(train_data.index)
            results["test_indices"].append(test_data_point.index)
            continue

        try:
            fitted_model = sm.OLS(y_train, X_train).fit()

            # Ensure test data columns match fitted model
            if not all(col in X_test.columns for col in fitted_model.params.index):
                missing = set(fitted_model.params.index) - set(X_test.columns)
                logging.error(
                    "Mismatch between fitted model params and test data columns "
                    "at index %d. Missing in test: %s",
                    i,
                    missing,
                )
                prediction = np.nan
            else:
                X_test_ordered = X_test[fitted_model.params.index]
                prediction = fitted_model.predict(X_test_ordered).iloc[0]

            actual = test_data_point[endog_col].iloc[0]
            residual = actual - prediction

            # Store results
            results["predictions"].append(prediction)
            results["actuals"].append(actual)
            results["residuals"].append(residual)
            results["models"].append(fitted_model)
            results["train_indices"].append(train_data.index)
            results["test_indices"].append(test_data_point.index)

        except Exception as e:  # pylint: disable=broad-except
            logging.error(
                "Error during OLS fitting or prediction for window ending at index %d: %s",
                i,
                e,
            )
            results["predictions"].append(np.nan)
            results["actuals"].append(
                test_data_point[endog_col].iloc[0]
                if endog_col in test_data_point
                else np.nan
            )
            results["residuals"].append(np.nan)
            results["models"].append(None)
            results["train_indices"].append(train_data.index)
            results["test_indices"].append(test_data_point.index)

    # Convert to numpy arrays
    results["predictions"] = np.array(results["predictions"])
    results["actuals"] = np.array(results["actuals"])
    results["residuals"] = np.array(results["residuals"])

    # Calculate OOS metrics
    valid_mask = ~np.isnan(results["predictions"]) & ~np.isnan(results["actuals"])

    if valid_mask.any():
        results["oos_rmse"] = np.sqrt(
            mean_squared_error(
                results["actuals"][valid_mask], results["predictions"][valid_mask]
            )
        )
        results["oos_mae"] = mean_absolute_error(
            results["actuals"][valid_mask], results["predictions"][valid_mask]
        )

        # Directional accuracy
        direction_actual = np.sign(np.diff(results["actuals"][valid_mask]))
        direction_pred = np.sign(np.diff(results["predictions"][valid_mask]))
        dir_mask = (direction_actual != 0) & (direction_pred != 0)
        results["oos_directional_accuracy"] = (
            np.mean(direction_actual[dir_mask] == direction_pred[dir_mask])
            if dir_mask.any()
            else np.nan
        )

        logging.info(
            "OOS Validation Complete. RMSE: %.4f, MAE: %.4f, Dir Acc: %.2f%%",
            results["oos_rmse"],
            results["oos_mae"],
            results["oos_directional_accuracy"] * 100
            if not np.isnan(results["oos_directional_accuracy"])
            else float("nan"),
        )
    else:
        logging.warning(
            "No valid predictions/actuals available; OOS metrics set to NaN."
        )
        results["oos_rmse"] = np.nan
        results["oos_mae"] = np.nan
        results["oos_directional_accuracy"] = np.nan

    return results
