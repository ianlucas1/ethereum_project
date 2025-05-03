# src/ols_models.py

import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error  # For RMSE calculation

# --- OLS Fitting Function ---


def fit_ols_hac(
    y: pd.Series, X: pd.DataFrame, add_const: bool = True, lags: int = 12
) -> dict:
    """
    Fits OLS model with HAC robust standard errors.

    Args:
        y: Endogenous variable (Pandas Series).
        X: Exogenous variables (Pandas DataFrame).
        add_const: Whether to add a constant to X.
        lags: Maximum lags for Newey-West estimator.

    Returns:
        A dictionary containing model results. Keys include:
            - 'model_obj': The fitted statsmodels result object (HAC adjusted). None on error.
            - 'params': Dictionary of coefficient estimates.
            - 'pvals_hac': Dictionary of HAC p-values.
            - 'se_hac': Dictionary of HAC standard errors.
            - 'r2': R-squared.
            - 'r2_adj': Adjusted R-squared.
            - 'n_obs': Number of observations used.
            - 'resid': Residuals (Pandas Series).
            - 'fittedvalues': Fitted values (Pandas Series).
            - 'model_formula': String representation of the model formula.
            - 'error': String description if fitting failed, else None.
    """
    if y is None or X is None:
        logging.error("OLS input y or X is None.")
        return {
            "model_obj": None,
            "error": "Input data is None.",
        }  # Return model_obj: None
    if not isinstance(y, pd.Series) or not isinstance(X, pd.DataFrame):
        logging.error("OLS input y must be Series, X must be DataFrame.")
        return {
            "model_obj": None,
            "error": "Incorrect input types.",
        }  # Return model_obj: None

    df = pd.concat([y, X], axis=1).dropna()
    y_name = y.name
    X_names = X.columns.tolist()

    if len(df) < len(X_names) + 5 + (1 if add_const else 0):  # Check degrees of freedom
        logging.warning(
            f"Skipping OLS for {y_name}: Insufficient observations ({len(df)}) after dropna."
        )
        return {
            "model_obj": None,
            "error": "Insufficient observations.",
        }  # Return model_obj: None

    y_fit = df[y_name]
    X_fit = df[X_names]
    if add_const:
        X_fit = sm.add_constant(X_fit, has_constant="add")
        model_col_names = ["const"] + X_names
    else:
        model_col_names = X_names

    try:
        model = sm.OLS(y_fit, X_fit)
        fit = model.fit()
        # Apply HAC robust standard errors
        hac_results = fit.get_robustcov_results(cov_type="HAC", maxlags=lags)

        params = dict(zip(model_col_names, hac_results.params))
        pvals = dict(zip(model_col_names, hac_results.pvalues))
        ses = dict(zip(model_col_names, hac_results.bse))

        return {
            "model_obj": hac_results,  # Store the HAC results object
            "params": params,
            "pvals_hac": pvals,
            "se_hac": ses,
            "r2": hac_results.rsquared,
            "r2_adj": hac_results.rsquared_adj,
            "n_obs": int(hac_results.nobs),
            "resid": hac_results.resid,  # Residuals from HAC object
            "fittedvalues": hac_results.fittedvalues,
            "model_formula": f"{y_name} ~ {' + '.join(X_fit.columns)} (HAC lags={lags})",
        }
    except Exception as e:
        logging.error(f"OLS fitting failed for {y_name}: {e}", exc_info=True)
        return {"model_obj": None, "error": str(e)}  # Return model_obj: None


# --- OLS Benchmark Analysis ---


def run_ols_benchmarks(daily_df: pd.DataFrame, monthly_df: pd.DataFrame) -> dict:
    """
    Runs baseline and extended OLS models on daily and monthly data.
    MODIFIES monthly_df by adding fair value columns.

    Args:
        daily_df: Cleaned daily data.
        monthly_df: Cleaned monthly data (will be modified).

    Returns:
        Dictionary containing results for different OLS specifications.
    """
    logging.info("Running Static OLS Benchmarks...")
    ols_results = {}
    ols_results["monthly_base"] = {}
    ols_results["monthly_extended"] = {}
    ols_results["monthly_constrained"] = {}  # For beta=2 check

    # Ensure required columns exist
    req_cols_monthly = [
        "log_marketcap",
        "log_active",
        "log_nasdaq",
        "log_gas",
        "price_usd",
        "supply",
    ]
    if not all(col in monthly_df.columns for col in req_cols_monthly):
        missing = set(req_cols_monthly) - set(monthly_df.columns)
        logging.error(f"Monthly DataFrame missing required columns for OLS: {missing}")
        return ols_results  # Return empty results

    # --- Monthly Baseline ---
    logging.info("Fitting Monthly Baseline OLS (log_marketcap ~ log_active)...")
    y_m = monthly_df["log_marketcap"]
    X_m_base = monthly_df[["log_active"]]
    res_m_base = fit_ols_hac(y_m, X_m_base, add_const=True, lags=12)
    ols_results["monthly_base"] = res_m_base

    if res_m_base.get("model_obj"):
        # Calculate Fair Value and RMSE for baseline
        try:
            p = res_m_base["params"]
            fv_log = p["const"] + p["log_active"] * monthly_df["log_active"]
            # Align index before division
            fv_log_aligned, supply_aligned = fv_log.align(
                monthly_df["supply"], join="inner"
            )
            # Add fair value column to the DataFrame passed in
            monthly_df["fair_price_base"] = np.exp(fv_log_aligned) / supply_aligned

            # Align prices before RMSE calculation
            actual_price_aligned, fair_price_aligned = monthly_df["price_usd"].align(
                monthly_df["fair_price_base"], join="inner"
            )
            valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()
            if valid_idx.sum() > 0:
                rmse_base = np.sqrt(
                    mean_squared_error(
                        actual_price_aligned[valid_idx], fair_price_aligned[valid_idx]
                    )
                )
                ols_results["monthly_base"]["RMSE_USD"] = rmse_base
                logging.info(
                    f"Monthly Base OLS: R2={res_m_base.get('r2', np.nan):.3f}, RMSE={rmse_base:.2f}"
                )
            else:
                ols_results["monthly_base"]["RMSE_USD"] = np.nan
                logging.warning(
                    "Could not calculate RMSE for monthly base OLS (no valid price pairs)."
                )

        except Exception as e:
            logging.error(
                f"Error calculating fair value/RMSE for monthly base OLS: {e}"
            )
            ols_results["monthly_base"]["RMSE_USD"] = np.nan

    # --- Monthly Extended ---
    logging.info(
        "Fitting Monthly Extended OLS (log_marketcap ~ log_active + log_nasdaq + log_gas)..."
    )
    X_m_ext_cols = ["log_active", "log_nasdaq", "log_gas"]
    X_m_ext = monthly_df[X_m_ext_cols]
    res_m_ext = fit_ols_hac(y_m, X_m_ext, add_const=True, lags=12)
    ols_results["monthly_extended"] = res_m_ext

    if res_m_ext.get("model_obj"):
        # Calculate Fair Value and RMSE for extended
        try:
            p_ext = res_m_ext["params"]
            fv_log_ext = (
                p_ext["const"]
                + p_ext["log_active"] * monthly_df["log_active"]
                + p_ext["log_nasdaq"] * monthly_df["log_nasdaq"]
                + p_ext["log_gas"] * monthly_df["log_gas"]
            )

            fv_log_ext_aligned, supply_aligned = fv_log_ext.align(
                monthly_df["supply"], join="inner"
            )
            # Add fair value column to the DataFrame passed in
            monthly_df["fair_price_ext"] = np.exp(fv_log_ext_aligned) / supply_aligned

            actual_price_aligned, fair_price_aligned = monthly_df["price_usd"].align(
                monthly_df["fair_price_ext"], join="inner"
            )
            valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()

            if valid_idx.sum() > 0:
                rmse_ext = np.sqrt(
                    mean_squared_error(
                        actual_price_aligned[valid_idx], fair_price_aligned[valid_idx]
                    )
                )
                ols_results["monthly_extended"]["RMSE_USD"] = rmse_ext
                logging.info(
                    f"Monthly Extended OLS: R2={res_m_ext.get('r2', np.nan):.3f}, RMSE={rmse_ext:.2f}"
                )
            else:
                ols_results["monthly_extended"]["RMSE_USD"] = np.nan
                logging.warning(
                    "Could not calculate RMSE for monthly extended OLS (no valid price pairs)."
                )

        except Exception as e:
            logging.error(
                f"Error calculating fair value/RMSE for monthly extended OLS: {e}"
            )
            ols_results["monthly_extended"]["RMSE_USD"] = np.nan

    # --- Monthly Constrained (Beta=2) ---
    if ols_results["monthly_base"].get("params"):
        try:
            alpha_hat = ols_results["monthly_base"]["params"]["const"]
            beta_fixed = 2.0
            fv_log_constr = alpha_hat + beta_fixed * monthly_df["log_active"]

            fv_log_constr_aligned, supply_aligned = fv_log_constr.align(
                monthly_df["supply"], join="inner"
            )
            # Add fair value column to the DataFrame passed in
            monthly_df["fair_price_constr"] = (
                np.exp(fv_log_constr_aligned) / supply_aligned
            )

            actual_price_aligned, fair_price_aligned = monthly_df["price_usd"].align(
                monthly_df["fair_price_constr"], join="inner"
            )
            valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()

            if valid_idx.sum() > 0:
                rmse_c = np.sqrt(
                    mean_squared_error(
                        actual_price_aligned[valid_idx], fair_price_aligned[valid_idx]
                    )
                )
                ols_results["monthly_constrained"] = {
                    "alpha": alpha_hat,
                    "beta": beta_fixed,
                    "RMSE_USD": rmse_c,
                }
                logging.info(f"Monthly Constrained (beta=2) OLS: RMSE={rmse_c:.2f}")
            else:
                ols_results["monthly_constrained"] = {
                    "alpha": alpha_hat,
                    "beta": beta_fixed,
                    "RMSE_USD": np.nan,
                }
                logging.warning(
                    "Could not calculate RMSE for monthly constrained OLS (no valid price pairs)."
                )

        except Exception as e:
            logging.error(
                f"Error calculating fair value/RMSE for monthly constrained OLS: {e}"
            )
            ols_results["monthly_constrained"] = {"RMSE_USD": np.nan}

    return ols_results
