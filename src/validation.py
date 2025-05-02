# src/validation.py 

import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

# --- Out-of-Sample Rolling Validation ---

def run_oos_validation(df_monthly: pd.DataFrame, endog_col: str, exog_cols: list[str],
                       window_size: int = 24, add_const: bool = True) -> dict:
    """
    Performs rolling out-of-sample validation using a simple OLS model.

    Args:
        df_monthly: Monthly DataFrame with all required columns.
        endog_col: Name of the endogenous variable (e.g., 'log_marketcap').
        exog_cols: List of exogenous variable names.
        window_size: Rolling window size in months.
        add_const: Whether to include a constant in the rolling OLS.

    Returns:
        Dictionary containing OOS metrics and predictions.
    """
    logging.info(f"Starting Out-of-Sample validation ({window_size}-month rolling window)...")
    oos_results = {}
    required_cols = [endog_col] + exog_cols + ['price_usd', 'supply'] # Need price/supply for metrics
    if not all(col in df_monthly.columns for col in required_cols):
         missing = set(required_cols) - set(df_monthly.columns)
         logging.error(f"Monthly DataFrame missing required columns for OOS: {missing}")
         return {"error": f"Missing columns: {missing}"}

    # Prepare data, drop initial NaNs if any
    model_df = df_monthly[required_cols].copy()
    # Drop rows where *any* required modeling variable is NaN
    model_df.dropna(subset=[endog_col] + exog_cols, inplace=True)

    n_months = len(model_df)
    if n_months < window_size + 1:
        logging.warning(f"Skipping OOS: Insufficient data ({n_months}) for window size ({window_size}).")
        return {"error": "Insufficient data."}

    actual_vals_price = []
    pred_vals_price = []
    oos_dates = []

    for end_idx in range(window_size, n_months):
        train_start_idx = end_idx - window_size
        train_data = model_df.iloc[train_start_idx:end_idx]
        test_data_point = model_df.iloc[end_idx:end_idx + 1] # The single next point to predict

        # Prepare data for window OLS
        y_train = train_data[endog_col]
        X_train = train_data[exog_cols]
        if add_const:
            X_train = sm.add_constant(X_train, has_constant='add')

        # Check for sufficient data and NaNs in window (redundant due to initial dropna?)
        if y_train.isnull().any() or X_train.isnull().any().any() or len(y_train) < X_train.shape[1] + 2:
             logging.warning(f"Skipping OOS window ending {train_data.index[-1].date()}: Insufficient data or NaNs in window.")
             continue

        try:
            # Fit OLS on window data (plain OLS for prediction coefficients)
            model_win = sm.OLS(y_train, X_train).fit()

            # Prepare test data point's regressors
            X_test = test_data_point[exog_cols]
            if add_const:
                X_test = sm.add_constant(X_test, has_constant='add')
                # Ensure columns match train columns (order and presence)
                X_test = X_test[X_train.columns]


            # Check if test point has NaNs in regressors
            if X_test.isnull().any().any():
                logging.warning(f"Skipping OOS prediction for {test_data_point.index[0].date()}: NaN in regressors.")
                continue

            # Predict log market cap for the next month
            pred_log = model_win.predict(X_test).iloc[0] # Use .iloc[0]
            actual_log = test_data_point[endog_col].iloc[0]
            actual_price = test_data_point['price_usd'].iloc[0]
            supply_oos = test_data_point['supply'].iloc[0]

            # Check if actual log/price/supply values are valid
            if pd.isna(actual_log) or pd.isna(actual_price) or pd.isna(supply_oos) or supply_oos == 0:
                logging.warning(f"Skipping OOS prediction for {test_data_point.index[0].date()}: NaN/invalid value in actuals/supply.")
                continue

            # Convert prediction back to price space
            # Handle potential overflow during exp()
            with np.errstate(over='ignore'):
                 pred_price = np.exp(pred_log) / supply_oos
                 if not np.isfinite(pred_price):
                      logging.warning(f"Overflow encountered calculating predicted price for {test_data_point.index[0].date()}. pred_log={pred_log}")
                      pred_price = np.nan # Set to NaN if overflow occurs

            pred_vals_price.append(pred_price)
            actual_vals_price.append(actual_price)
            oos_dates.append(test_data_point.index[0])

        except Exception as e:
            logging.error(f"ERROR during OOS window ending {train_data.index[-1].date()}: {e}", exc_info=True)
            continue # Skip to next window

    if actual_vals_price and pred_vals_price:
        actual_np = np.array(actual_vals_price)
        pred_np = np.array(pred_vals_price)

        # Calculate metrics using Price values
        # Avoid division by zero or invalid values in MAPE
        valid_mape_idx = (actual_np > 1e-6) & np.isfinite(actual_np) & np.isfinite(pred_np)
        if valid_mape_idx.sum() > 0:
             mape = mean_absolute_percentage_error(actual_np[valid_mape_idx], pred_np[valid_mape_idx]) * 100
        else:
             mape = np.nan

        # Calculate RMSE only on valid, finite pairs
        valid_rmse_idx = np.isfinite(actual_np) & np.isfinite(pred_np)
        if valid_rmse_idx.sum() > 0:
            rmse = np.sqrt(mean_squared_error(actual_np[valid_rmse_idx], pred_np[valid_rmse_idx]))
        else:
            rmse = np.nan

        oos_results = {
            'MAPE_percent': mape,
            'RMSE_Price': rmse,
            'N_OOS': len(actual_vals_price),
            'predictions_df': pd.DataFrame({
                'actual_price': actual_vals_price,
                'predicted_price_oos': pred_vals_price
            }, index=pd.to_datetime(oos_dates))
        }
        logging.info(f"Out-of-Sample Results: N={oos_results['N_OOS']}, MAPE={mape:.1f}%, RMSE_Price=${rmse:,.2f}")

    else:
        logging.warning("No OOS predictions were generated.")
        oos_results = {'MAPE_percent': np.nan, 'RMSE_Price': np.nan, 'N_OOS': 0, 'error': 'No predictions generated.'}

    return oos_results 