"""Model validation functions, primarily focusing on out-of-sample performance."""

from __future__ import annotations

import logging
from typing import Any, Dict, List  # Use specific types

import numpy as np
import pandas as pd
import statsmodels.api as sm

# Import specific statsmodels types for hinting
from statsmodels.regression.linear_model import RegressionResultsWrapper
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.eda import run_stationarity_tests, winsorize_data

# --- Out-of-Sample Rolling Validation --------------------------------------------------


def run_oos_validation(
    df_monthly: pd.DataFrame,
    endog_col: str,
    exog_cols: List[str],
    winsorize_cols: List[str],
    winsorize_quantile: float,
    stationarity_cols: List[str],
    window_size: int = 24,
    add_const: bool = True,
) -> Dict[str, Any]:
    """Performs rolling out-of-sample (OOS) validation for an OLS model.

    Iteratively trains an OLS model on a rolling window of past data and
    predicts the next observation. Preprocessing steps (winsorization,
    stationarity tests) are applied *within* each training window to avoid
    lookahead bias. Calculates standard OOS performance metrics (RMSE, MAE,
    Directional Accuracy).

    Args:
        df_monthly (pd.DataFrame): Monthly DataFrame with features and target.
                                   Must contain columns specified in endog_col,
                                   exog_cols, winsorize_cols, stationarity_cols.
        endog_col (str): Name of the endogenous (target) variable column.
        exog_cols (List[str]): List of exogenous (feature) variable column names.
        winsorize_cols (List[str]): List of columns to winsorize within each
                                    training window.
        winsorize_quantile (float): The upper quantile (e.g., 0.99) to use for
                                    winsorizing.
        stationarity_cols (List[str]): List of columns to test for stationarity
                                       within each training window (results logged).
        window_size (int): The size of the rolling training window (in months).
                           Defaults to 24.
        add_const (bool): Whether to add a constant term to the exogenous
                          variables for the OLS model. Defaults to True.

    Returns:
        Dict[str, Any]: A dictionary containing OOS validation results:
            - 'predictions' (np.ndarray): Array of predicted values.
            - 'actuals' (np.ndarray): Array of actual values.
            - 'residuals' (np.ndarray): Array of residuals (actual - prediction).
            - 'models' (List[RegressionResultsWrapper | None]): List of fitted
              statsmodels OLS result objects for each window (None if fit failed).
            - 'train_indices' (List[pd.Index]): List of training data indices for each window.
            - 'test_indices' (List[pd.Index]): List of test data indices for each window.
            - 'oos_rmse' (float | np.nan): Root Mean Squared Error of predictions.
            - 'oos_mae' (float | np.nan): Mean Absolute Error of predictions.
            - 'oos_directional_accuracy' (float | np.nan): Percentage of times the
              predicted direction matched the actual direction (ignores zero changes).
            - 'N_OOS' (int): Number of valid OOS predictions made.
            - 'predictions_df' (pd.DataFrame): DataFrame containing predictions indexed by date.
            Metrics are np.nan if no valid predictions could be made.
    """
    logging.info(
        f"Starting OOS validation for '{endog_col}' ~ {' + '.join(exog_cols)} "
        f"with window size {window_size}."
    )

    # Initialize results structure
    results: Dict[str, Any] = {
        "predictions": [],
        "actuals": [],
        "residuals": [],
        "models": [],
        "train_indices": [],
        "test_indices": [],
        "oos_rmse": np.nan,  # Initialize metrics to NaN
        "oos_mae": np.nan,
        "oos_directional_accuracy": np.nan,
        "N_OOS": 0,
        "predictions_df": pd.DataFrame(),  # Initialize as empty DataFrame
    }

    n_obs: int = len(df_monthly)

    # Check if enough data for at least one window + 1 prediction
    if n_obs < window_size + 1:
        logging.error(
            f"Insufficient data ({n_obs} obs) for OOS validation with window size "
            f"{window_size}. Need at least {window_size + 1}."
        )
        return results  # Return initialized (mostly empty) results

    # Rolling window loop
    for i in range(window_size, n_obs):
        train_start_index: int = i - window_size
        train_end_index: int = i
        test_index: int = i

        train_data: pd.DataFrame = df_monthly.iloc[train_start_index:train_end_index]
        test_data_point: pd.DataFrame = df_monthly.iloc[
            [test_index]
        ]  # iloc[[i]] keeps it as DataFrame

        # Store indices for this iteration
        results["train_indices"].append(train_data.index)
        results["test_indices"].append(test_data_point.index)

        # --- In-window Preprocessing ---
        # Winsorize the training data for this window only
        train_data_winsorized: pd.DataFrame = winsorize_data(
            df=train_data,
            cols_to_cap=winsorize_cols,
            quantile=winsorize_quantile,
            window_mask=None,  # Apply to the whole train_data slice
        )

        # Run stationarity tests on the winsorized training data for this window
        if stationarity_cols:
            try:
                # Ensure index is DatetimeIndex before accessing date attributes
                if isinstance(train_data.index, pd.DatetimeIndex):
                    window_end_date_str = train_data.index[-1].strftime("%Y-%m-%d")
                    logging.debug(
                        "Running stationarity tests for OOS window ending %s",
                        window_end_date_str,
                    )
                    stationarity_results_window: pd.DataFrame = run_stationarity_tests(
                        df=train_data_winsorized,
                        cols_to_test=stationarity_cols,
                        window_mask=None,  # Test the whole slice
                    )
                    logging.debug(
                        "Stationarity Results (Window %s):\n%s",
                        window_end_date_str,
                        stationarity_results_window.to_string(),
                    )
                else:
                    logging.debug(
                        "Skipping stationarity test logging: Index is not DatetimeIndex."
                    )
            except Exception as stat_e:
                logging.warning(
                    f"Stationarity test failed for window ending at index {i}: {stat_e}"
                )

        # --- Prepare data for OLS ---
        try:
            y_train: pd.Series = train_data_winsorized[endog_col]
            X_train_df: pd.DataFrame = train_data_winsorized[exog_cols]
            # Prepare test data point using original (non-winsorized) test data
            # Exog variables for prediction should come from the actual test point
            X_test_df: pd.DataFrame = test_data_point[exog_cols]

            # Add constant if required
            X_train_fit: pd.DataFrame
            X_test_fit: pd.DataFrame
            if add_const:
                X_train_fit = sm.add_constant(X_train_df, has_constant="add")
                X_test_fit = sm.add_constant(X_test_df, has_constant="add")
            else:
                X_train_fit = X_train_df
                X_test_fit = X_test_df

            # Skip window if NaNs remain after preprocessing and selection
            if X_train_fit.isnull().any().any() or y_train.isnull().any():
                logging.warning(
                    f"NaNs found in training data for window ending at index {i}. Skipping."
                )
                results["predictions"].append(np.nan)
                results["actuals"].append(test_data_point[endog_col].iloc[0])
                results["residuals"].append(np.nan)
                results["models"].append(None)
                continue  # Skip to next iteration

        except KeyError as ke:
            logging.error(
                f"Missing column during OOS data prep at index {i}: {ke}. Skipping window."
            )
            results["predictions"].append(np.nan)
            results["actuals"].append(
                np.nan
            )  # Actual might also be unavailable if endog_col missing
            results["residuals"].append(np.nan)
            results["models"].append(None)
            continue
        except Exception as prep_e:
            logging.error(
                f"Error preparing OOS data at index {i}: {prep_e}", exc_info=True
            )
            results["predictions"].append(np.nan)
            results["actuals"].append(np.nan)
            results["residuals"].append(np.nan)
            results["models"].append(None)
            continue

        # --- Fit OLS and Predict ---
        prediction: float | np.float64 | np.ndarray[Any, Any] | pd.Series = (
            np.nan
        )  # Initialize prediction
        try:
            # Fit model on (potentially winsorized) training data
            fitted_model: RegressionResultsWrapper = sm.OLS(y_train, X_train_fit).fit()

            # Ensure test data columns match fitted model params (after add_constant)
            model_params_index: pd.Index = fitted_model.params.index
            if not all(col in X_test_fit.columns for col in model_params_index):
                missing = set(model_params_index) - set(X_test_fit.columns)
                logging.error(
                    f"Mismatch between fitted model params and test data columns "
                    f"at index {i}. Missing in test: {missing}. Skipping prediction."
                )
                # prediction remains np.nan
            else:
                # Reorder test data columns to match model parameters
                X_test_ordered: pd.DataFrame = X_test_fit[model_params_index]
                # Predict using the single row of (potentially constant-added) test data
                prediction_series: pd.Series = fitted_model.predict(X_test_ordered)
                if not prediction_series.empty:
                    prediction = prediction_series.iloc[
                        0
                    ]  # Get the single prediction value

            actual: Any = test_data_point[endog_col].iloc[0]  # Get actual value
            residual: Any = np.nan  # Default residual to NaN
            # Calculate residual only if prediction and actual are valid numbers
            if pd.notna(prediction) and pd.notna(actual):
                try:
                    residual = float(actual) - float(prediction)
                except (ValueError, TypeError):
                    logging.warning(
                        f"Could not calculate residual at index {i} due to non-numeric types."
                    )
                    residual = np.nan  # Ensure it's NaN if calculation fails

            # Store results for this window
            results["predictions"].append(prediction)
            results["actuals"].append(actual)
            results["residuals"].append(residual)
            results["models"].append(fitted_model)

        except Exception as e:
            logging.error(
                f"Error during OLS fitting or prediction for window ending at index {i}: {e}",
                exc_info=True,
            )
            results["predictions"].append(np.nan)
            # Try to get actual even if prediction fails
            actual_on_fail = np.nan
            try:
                actual_on_fail = test_data_point[endog_col].iloc[0]
            except KeyError:
                pass  # Keep as NaN if endog_col missing
            results["actuals"].append(actual_on_fail)
            results["residuals"].append(np.nan)
            results["models"].append(None)

    # --- Calculate Overall OOS Metrics ---
    # Convert lists to numpy arrays for vectorized operations
    predictions_arr = np.array(results["predictions"], dtype=float)
    actuals_arr = np.array(
        results["actuals"], dtype=float
    )  # Attempt conversion to float

    # Create mask for valid (non-NaN) pairs
    valid_mask = ~np.isnan(predictions_arr) & ~np.isnan(actuals_arr)

    if valid_mask.sum() > 0:  # Check if there are any valid pairs
        valid_actuals = actuals_arr[valid_mask]
        valid_predictions = predictions_arr[valid_mask]

        results["oos_rmse"] = np.sqrt(
            mean_squared_error(valid_actuals, valid_predictions)
        )
        results["oos_mae"] = mean_absolute_error(valid_actuals, valid_predictions)

        # Directional accuracy (requires at least 2 valid points)
        if valid_mask.sum() >= 2:
            direction_actual = np.sign(np.diff(valid_actuals))
            direction_pred = np.sign(np.diff(valid_predictions))
            # Compare only where both actual and predicted changes are non-zero
            dir_mask = (direction_actual != 0) & (direction_pred != 0)
            if dir_mask.sum() > 0:
                results["oos_directional_accuracy"] = np.mean(
                    direction_actual[dir_mask] == direction_pred[dir_mask]
                )
            else:
                results["oos_directional_accuracy"] = (
                    np.nan
                )  # No non-zero changes to compare
        else:
            results["oos_directional_accuracy"] = np.nan  # Not enough points for diff

        logging.info(
            "OOS Validation Complete. RMSE: %.4f, MAE: %.4f, Dir Acc: %.2f%%",
            results["oos_rmse"],
            results["oos_mae"],
            results["oos_directional_accuracy"] * 100
            if pd.notna(results["oos_directional_accuracy"])
            else float("nan"),  # Use float('nan') for consistency
        )
    else:
        logging.warning(
            "No valid OOS predictions/actuals available; metrics remain NaN."
        )
        # Metrics already initialized to NaN

    # Add N_OOS count
    results["N_OOS"] = int(valid_mask.sum())

    # Add predictions back to original df index (handle potential index mismatches)
    # Create a Series with the correct index from test_indices
    valid_test_indices = [
        idx[0] for idx in results["test_indices"] if idx
    ]  # Get valid indices
    if len(valid_test_indices) == len(results["predictions"]):  # Check length match
        oos_pred_series = pd.Series(
            results["predictions"],
            index=valid_test_indices,
            name="predicted_price_oos",  # Match name used in reporting
        )
        # Add this series to the results dict for reporting function to use
        results["predictions_df"] = oos_pred_series.to_frame()
    else:
        logging.warning(
            "Length mismatch between predictions and test indices. Cannot create predictions_df."
        )
        results["predictions_df"] = pd.DataFrame()  # Assign empty df

    return results
