"""Ordinary Least Squares (OLS) model implementations.

Provides functions for fitting OLS models with Heteroskedasticity and
Autocorrelation Consistent (HAC) standard errors (Newey-West), and for
running benchmark OLS analyses (baseline, extended, constrained).
"""

from __future__ import annotations

import logging
from typing import Any, Dict  # Added Dict

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import mean_squared_error

# Import specific statsmodels types for hinting
from statsmodels.regression.linear_model import OLS, RegressionResultsWrapper

# --- OLS Fitting Function ---


def fit_ols_hac(
    y: pd.Series, X: pd.DataFrame, add_const: bool = True, lags: int = 12
) -> Dict[str, Any]:
    """Fits OLS model with HAC robust standard errors (Newey-West).

    Handles NaN dropping, checks for sufficient observations, adds a constant
    if requested, fits the model, and computes HAC standard errors.

    Args:
        y (pd.Series): Endogenous variable (dependent variable).
        X (pd.DataFrame): Exogenous variables (independent variables).
        add_const (bool): Whether to add a constant term to X. Defaults to True.
        lags (int): Maximum number of lags for the Newey-West estimator. Defaults to 12.

    Returns:
        Dict[str, Any]: A dictionary containing model results. Keys include:
            - 'model_obj' (RegressionResultsWrapper | None): The fitted statsmodels
              results object with HAC errors. None if fitting failed.
            - 'params' (Dict[str, float]): Dictionary of coefficient estimates.
            - 'pvals_hac' (Dict[str, float]): Dictionary of HAC p-values.
            - 'se_hac' (Dict[str, float]): Dictionary of HAC standard errors.
            - 'r2' (float): R-squared value.
            - 'r2_adj' (float): Adjusted R-squared value.
            - 'n_obs' (int): Number of observations used in the estimation.
            - 'resid' (pd.Series): Residuals from the fitted model.
            - 'fittedvalues' (pd.Series): Fitted values from the model.
            - 'model_formula' (str): String representation of the fitted model.
            - 'error' (str | None): String description if fitting failed, else None.
            Values for statistical metrics will be np.nan or None if fitting fails.
    """
    results: Dict[str, Any] = {  # Initialize results dict
        "model_obj": None,
        "params": {},
        "pvals_hac": {},
        "se_hac": {},
        "r2": np.nan,
        "r2_adj": np.nan,
        "n_obs": 0,
        "resid": pd.Series(dtype=float),
        "fittedvalues": pd.Series(dtype=float),
        "model_formula": "",
        "error": None,
    }
    if y is None or X is None:
        logging.error("OLS input y or X is None.")
        results["error"] = "Input data is None."
        return results
    if not isinstance(y, pd.Series) or not isinstance(X, pd.DataFrame):
        logging.error("OLS input y must be Series, X must be DataFrame.")
        results["error"] = "Incorrect input types."
        return results

    # Combine and drop NaNs for fitting
    df_fit = pd.concat([y, X], axis=1).dropna()
    y_name: str = str(y.name) if y.name is not None else "y"  # Handle unnamed Series
    X_names: list[str] = X.columns.tolist()

    min_obs_needed = len(X_names) + (1 if add_const else 0) + 1  # Need > k regressors
    if len(df_fit) < min_obs_needed:
        logging.warning(
            f"Skipping OLS for {y_name}: Insufficient observations ({len(df_fit)}) "
            f"after dropna. Need at least {min_obs_needed}."
        )
        results["error"] = "Insufficient observations."
        return results

    y_fit: pd.Series = df_fit[y_name]
    X_fit_df: pd.DataFrame = df_fit[X_names]  # Keep as DataFrame before adding constant

    # Determine the DataFrame to use for fitting (with or without constant)
    if add_const:
        X_fit_const: pd.DataFrame = sm.add_constant(X_fit_df, has_constant="add")
        X_to_fit = X_fit_const  # Use the DataFrame with constant for fitting
    else:
        X_to_fit = X_fit_df  # Use the original DataFrame

    try:
        model: OLS = sm.OLS(y_fit, X_to_fit)
        fit: RegressionResultsWrapper = model.fit()
        # Apply HAC robust standard errors
        hac_results: RegressionResultsWrapper = fit.get_robustcov_results(
            cov_type="HAC", maxlags=lags
        )

        # Ensure params, pvals, ses are floats, handle potential non-numeric types gracefully
        params_dict: Dict[str, float] = {
            k: float(v) if pd.notna(v) else np.nan
            for k, v in hac_results.params.items()
        }
        pvals_dict: Dict[str, float] = {
            k: float(v) if pd.notna(v) else np.nan
            for k, v in hac_results.pvalues.items()
        }
        ses_dict: Dict[str, float] = {
            k: float(v) if pd.notna(v) else np.nan for k, v in hac_results.bse.items()
        }

        results.update(
            {
                "model_obj": hac_results,
                "params": params_dict,
                "pvals_hac": pvals_dict,
                "se_hac": ses_dict,
                "r2": float(hac_results.rsquared)
                if pd.notna(hac_results.rsquared)
                else np.nan,
                "r2_adj": float(hac_results.rsquared_adj)
                if pd.notna(hac_results.rsquared_adj)
                else np.nan,
                "n_obs": int(hac_results.nobs),
                "resid": hac_results.resid,
                "fittedvalues": hac_results.fittedvalues,
                # Use columns from the actual DataFrame used for fitting
                "model_formula": f"{y_name} ~ {' + '.join(X_to_fit.columns)} (HAC lags={lags})",
                "error": None,
            }
        )
        return results

    except Exception as e:
        # Handle singular matrix or invalid inputs
        except_types = (np.linalg.LinAlgError, ValueError)
        log_msg = f"OLS fit failed for {y_name}"
        if isinstance(e, except_types):
            log_msg += " due to linear algebra or value error"
            logging.exception(log_msg)  # Log exception for these specific types
        else:
            log_msg += f" with unexpected error: {e}"
            logging.exception(log_msg)  # Log exception for unexpected errors

        results["error"] = str(e)
        return results


# --- OLS Benchmark Analysis ---


def run_ols_benchmarks(
    daily_df: pd.DataFrame, monthly_df: pd.DataFrame
) -> Dict[str, Any]:
    """Runs baseline, extended, and constrained OLS models on monthly data.

    Fits three OLS models using `fit_ols_hac` on the provided monthly data:
    1. Baseline: log_marketcap ~ log_active
    2. Extended: log_marketcap ~ log_active + log_nasdaq + log_gas
    3. Constrained: Calculates RMSE assuming beta(log_active) = 2, using the
       intercept from the baseline model.

    This function MODIFIES the input `monthly_df` by adding columns for
    calculated fair values ('fair_price_base', 'fair_price_ext', 'fair_price_constr').

    Args:
        daily_df (pd.DataFrame): Cleaned daily data (currently unused, but kept
                                 for potential future use or signature consistency).
        monthly_df (pd.DataFrame): Cleaned monthly data containing required columns
                                   (log_marketcap, log_active, log_nasdaq, log_gas,
                                   price_usd, supply). This DataFrame *will be modified*.

    Returns:
        Dict[str, Any]: A dictionary containing results for the different OLS
                        specifications ('monthly_base', 'monthly_extended',
                        'monthly_constrained'). Each value is a dictionary
                        similar to the one returned by `fit_ols_hac`, potentially
                        with an added 'RMSE_USD' key. Returns partially filled
                        dictionary if required columns are missing.
    """
    logging.info("Running Static OLS Benchmarks...")
    ols_results: Dict[str, Any] = {
        "monthly_base": {},
        "monthly_extended": {},
        "monthly_constrained": {},  # For beta=2 check
    }

    # Ensure required columns exist in monthly data
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
        # Return partially filled results dict indicating the issue
        ols_results["error"] = f"Missing required monthly columns: {missing}"
        return ols_results

    # --- Monthly Baseline ---
    logging.info("Fitting Monthly Baseline OLS (log_marketcap ~ log_active)...")
    y_m_base: pd.Series = monthly_df["log_marketcap"]
    X_m_base: pd.DataFrame = monthly_df[["log_active"]]
    res_m_base = fit_ols_hac(y_m_base, X_m_base, add_const=True, lags=12)
    ols_results["monthly_base"] = res_m_base

    # Calculate Fair Value and RMSE for baseline if model fitting succeeded
    if res_m_base.get("model_obj") and res_m_base.get("error") is None:
        try:
            params_base = res_m_base["params"]
            # Ensure required params exist before calculation
            if "const" in params_base and "log_active" in params_base:
                fv_log_base = (
                    params_base["const"]
                    + params_base["log_active"] * monthly_df["log_active"]
                )
                # Align index before division
                fv_log_aligned, supply_aligned = fv_log_base.align(
                    monthly_df["supply"], join="inner"
                )
                # Add fair value column to the DataFrame passed in
                monthly_df["fair_price_base"] = np.exp(fv_log_aligned) / supply_aligned

                # Align prices before RMSE calculation
                actual_price_aligned, fair_price_aligned = monthly_df[
                    "price_usd"
                ].align(monthly_df["fair_price_base"], join="inner")
                valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()
                if valid_idx.sum() > 0:
                    rmse_base = np.sqrt(
                        mean_squared_error(
                            actual_price_aligned[valid_idx],
                            fair_price_aligned[valid_idx],
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
            else:
                logging.warning(
                    "Missing required parameters ('const', 'log_active') for base fair value calculation."
                )
                ols_results["monthly_base"]["RMSE_USD"] = np.nan

        except (ValueError, KeyError, TypeError, AttributeError) as e:
            logging.exception(
                f"Error calculating fair value/RMSE for monthly base OLS: {e}"
            )
            ols_results["monthly_base"]["RMSE_USD"] = np.nan

    # --- Monthly Extended ---
    logging.info(
        "Fitting Monthly Extended OLS (log_marketcap ~ log_active + log_nasdaq + log_gas)..."
    )
    y_m_ext: pd.Series = monthly_df["log_marketcap"]  # Can reuse y_m_base
    X_m_ext_cols = ["log_active", "log_nasdaq", "log_gas"]
    X_m_ext: pd.DataFrame = monthly_df[X_m_ext_cols]
    res_m_ext = fit_ols_hac(y_m_ext, X_m_ext, add_const=True, lags=12)
    ols_results["monthly_extended"] = res_m_ext

    # Calculate Fair Value and RMSE for extended if model fitting succeeded
    if res_m_ext.get("model_obj") and res_m_ext.get("error") is None:
        try:
            params_ext = res_m_ext["params"]
            # Ensure required params exist
            if all(
                k in params_ext
                for k in ["const", "log_active", "log_nasdaq", "log_gas"]
            ):
                fv_log_ext = (
                    params_ext["const"]
                    + params_ext["log_active"] * monthly_df["log_active"]
                    + params_ext["log_nasdaq"] * monthly_df["log_nasdaq"]
                    + params_ext["log_gas"] * monthly_df["log_gas"]
                )

                fv_log_ext_aligned, supply_aligned = fv_log_ext.align(
                    monthly_df["supply"], join="inner"
                )
                # Add fair value column to the DataFrame passed in
                monthly_df["fair_price_ext"] = (
                    np.exp(fv_log_ext_aligned) / supply_aligned
                )

                actual_price_aligned, fair_price_aligned = monthly_df[
                    "price_usd"
                ].align(monthly_df["fair_price_ext"], join="inner")
                valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()

                if valid_idx.sum() > 0:
                    rmse_ext = np.sqrt(
                        mean_squared_error(
                            actual_price_aligned[valid_idx],
                            fair_price_aligned[valid_idx],
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
            else:
                logging.warning(
                    "Missing required parameters for extended fair value calculation."
                )
                ols_results["monthly_extended"]["RMSE_USD"] = np.nan

        except (ValueError, KeyError, TypeError, AttributeError) as e:
            logging.exception(
                f"Error calculating fair value/RMSE for monthly extended OLS: {e}"
            )
            ols_results["monthly_extended"]["RMSE_USD"] = np.nan

    # --- Monthly Constrained (Beta=2) ---
    # Calculate only if baseline model succeeded and params are available
    if (
        ols_results["monthly_base"].get("params")
        and ols_results["monthly_base"].get("error") is None
    ):
        try:
            alpha_hat = ols_results["monthly_base"]["params"].get("const")
            if alpha_hat is not None and pd.notna(alpha_hat):
                beta_fixed = 2.0
                fv_log_constr = alpha_hat + beta_fixed * monthly_df["log_active"]

                fv_log_constr_aligned, supply_aligned = fv_log_constr.align(
                    monthly_df["supply"], join="inner"
                )
                # Add fair value column to the DataFrame passed in
                monthly_df["fair_price_constr"] = (
                    np.exp(fv_log_constr_aligned) / supply_aligned
                )

                actual_price_aligned, fair_price_aligned = monthly_df[
                    "price_usd"
                ].align(monthly_df["fair_price_constr"], join="inner")
                valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()

                if valid_idx.sum() > 0:
                    rmse_c = np.sqrt(
                        mean_squared_error(
                            actual_price_aligned[valid_idx],
                            fair_price_aligned[valid_idx],
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
            else:
                logging.warning(
                    "Could not retrieve 'const' parameter from baseline model for constrained calculation."
                )
                ols_results["monthly_constrained"] = {"RMSE_USD": np.nan}

        except (ValueError, KeyError, TypeError, AttributeError) as e:
            logging.exception(
                f"Error calculating fair value/RMSE for monthly constrained OLS: {e}"
            )
            ols_results["monthly_constrained"] = {"RMSE_USD": np.nan}
    else:
        logging.warning(
            "Skipping constrained OLS calculation as baseline model failed or params unavailable."
        )
        ols_results["monthly_constrained"] = {"RMSE_USD": np.nan}

    return ols_results
