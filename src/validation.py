# src/validation.py

import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm
from src.eda import winsorize_data, run_stationarity_tests
from sklearn.metrics import mean_squared_error, mean_absolute_error
from typing import Any, Dict

# --- Out-of-Sample Rolling Validation ---


def run_oos_validation(
    df_monthly: pd.DataFrame,
    endog_col: str,
    exog_cols: list[str],
    winsorize_cols: list[str],
    winsorize_quantile: float,
    stationarity_cols: list[str],
    window_size: int = 24,
    add_const: bool = True,
) -> dict:
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
        A dictionary containing OOS predictions, actuals, residuals, and metrics.
    """
    logging.info(
        f"Starting OOS validation for '{endog_col}' ~ {' + '.join(exog_cols)} with window size {window_size}."
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
            f"Insufficient data ({n_obs} obs) for OOS validation with window size {window_size}. Need at least {window_size + 1}."
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
            window_mask=train_data.index,  # Use current window's index
        )

        # Run stationarity tests on the winsorized training data for this window
        if stationarity_cols:  # Only run if columns are specified
            window_end_date = train_data.index[
                -1
            ].date()  # Use original train_data for date
            logging.debug(
                f"Running stationarity tests for OOS window ending {window_end_date}"
            )
            # Run on the already-sliced (and potentially winsorized) data for this window
            stationarity_results_window = run_stationarity_tests(
                df=train_data_winsorized,
                cols_to_test=stationarity_cols,
                window_mask=None,  # Test the entire slice passed as df
            )
            # Log the results table (or process/store if needed later)
            logging.debug(
                f"Stationarity Results (Window {window_end_date}):\n{stationarity_results_window.to_string()}"
            )
            # Note: Results are not currently stored in the main output dict

        # Use winsorized data for fitting
        y_train = train_data_winsorized[endog_col]
        X_train = train_data_winsorized[exog_cols]

        # Prepare test data (ensure same columns as training, including constant if added)
        X_test = test_data_point[exog_cols]

        if add_const:
            X_train = sm.add_constant(X_train, has_constant="add")
            X_test = sm.add_constant(
                X_test, has_constant="add"
            )  # Add constant to test set too

        # Check for NaNs after adding constant and before fitting
        if X_train.isnull().any().any() or y_train.isnull().any():
            logging.warning(
                f"NaNs found in training data for window ending at index {i}. Skipping this window."
            )
            # Append NaNs or handle as appropriate for your metrics later
            results["predictions"].append(np.nan)
            results["actuals"].append(test_data_point[endog_col].iloc[0])
            results["residuals"].append(np.nan)
            results["models"].append(None)
            results["train_indices"].append(train_data.index)
            results["test_indices"].append(test_data_point.index)
            continue

        try:
            model = sm.OLS(y_train, X_train)
            fitted_model = model.fit()

            # Ensure test data columns match fitted model's exog names
            if not all(col in X_test.columns for col in fitted_model.params.index):
                missing_in_test = set(fitted_model.params.index) - set(X_test.columns)
                logging.error(
                    f"Mismatch between fitted model params and test data columns at index {i}. Missing in test: {missing_in_test}"
                )
                # Handle error: skip prediction, append NaN, etc.
                prediction = np.nan
            else:
                # Reorder test data columns to match the model's expectation exactly
                X_test_ordered = X_test[fitted_model.params.index]
                prediction = fitted_model.predict(X_test_ordered).iloc[0]

            actual = test_data_point[endog_col].iloc[0]
            residual = actual - prediction

            results["predictions"].append(prediction)
            results["actuals"].append(actual)
            results["residuals"].append(residual)
            results["models"].append(fitted_model)  # Store the fitted model
            results["train_indices"].append(train_data.index)
            results["test_indices"].append(test_data_point.index)

        except Exception as e:
            logging.error(
                f"Error during OLS fitting or prediction for window ending at index {i}: {e}"
            )
            # Append NaNs or handle error case
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

    # Convert lists to numpy arrays for easier calculation
    results["predictions"] = np.array(results["predictions"])
    results["actuals"] = np.array(results["actuals"])
    results["residuals"] = np.array(results["residuals"])

    # Calculate OOS metrics, handling potential NaNs
    valid_preds = ~np.isnan(results["predictions"])
    valid_actuals = ~np.isnan(results["actuals"])
    valid_mask = valid_preds & valid_actuals

    if np.sum(valid_mask) > 0:
        results["oos_rmse"] = np.sqrt(
            mean_squared_error(
                results["actuals"][valid_mask], results["predictions"][valid_mask]
            )
        )
        results["oos_mae"] = mean_absolute_error(
            results["actuals"][valid_mask], results["predictions"][valid_mask]
        )
        # Simple directional accuracy
        direction_actual = np.sign(np.diff(results["actuals"][valid_mask]))
        direction_pred = np.sign(np.diff(results["predictions"][valid_mask]))
        # Ensure comparison is valid (handle zeros if necessary, here ignoring 0 changes)
        valid_dir_mask = (direction_actual != 0) & (direction_pred != 0)
        if np.sum(valid_dir_mask) > 0:
            results["oos_directional_accuracy"] = np.mean(
                direction_actual[valid_dir_mask] == direction_pred[valid_dir_mask]
            )
        else:
            results["oos_directional_accuracy"] = (
                np.nan
            )  # Not enough non-zero changes to calculate
        logging.info(
            f"OOS Validation Complete. RMSE: {results['oos_rmse']:.4f}, MAE: {results['oos_mae']:.4f}, Dir Acc: {results.get('oos_directional_accuracy', 'N/A'):.2%}"
        )
    else:
        logging.warning(
            "No valid predictions/actuals available to calculate OOS metrics."
        )
        results["oos_rmse"] = np.nan
        results["oos_mae"] = np.nan
        results["oos_directional_accuracy"] = np.nan

    return results
