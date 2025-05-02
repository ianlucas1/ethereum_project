# src/modeling.py

import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen
from statsmodels.tsa.ardl import ARDL, UECM, ardl_select_order
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.diagnostic import (
    acorr_breusch_godfrey, het_breuschpagan, het_white, breaks_cusumolsresid
)
from statsmodels.tools.sm_exceptions import SpecificationWarning, InterpolationWarning # Added InterpolationWarning
from scipy.stats import jarque_bera, f
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error # For OOS
import warnings # <-- Added import

# --- OLS Fitting Function ---

def fit_ols_hac(y: pd.Series, X: pd.DataFrame, add_const: bool = True, lags: int = 12) -> dict:
    """
    Fits OLS model with HAC robust standard errors.

    Args:
        y: Endogenous variable (Pandas Series).
        X: Exogenous variables (Pandas DataFrame).
        add_const: Whether to add a constant to X.
        lags: Maximum lags for Newey-West estimator.

    Returns:
        A dictionary containing model results (fit object, params, pvals, etc.).
    """
    if y is None or X is None:
        logging.error("OLS input y or X is None.")
        return {"model_obj": None, "error": "Input data is None."} # Return model_obj: None
    if not isinstance(y, pd.Series) or not isinstance(X, pd.DataFrame):
        logging.error("OLS input y must be Series, X must be DataFrame.")
        return {"model_obj": None, "error": "Incorrect input types."} # Return model_obj: None

    df = pd.concat([y, X], axis=1).dropna()
    y_name = y.name
    X_names = X.columns.tolist()

    if len(df) < len(X_names) + 5 + (1 if add_const else 0): # Check degrees of freedom
        logging.warning(f"Skipping OLS for {y_name}: Insufficient observations ({len(df)}) after dropna.")
        return {"model_obj": None, "error": "Insufficient observations."} # Return model_obj: None

    y_fit = df[y_name]
    X_fit = df[X_names]
    if add_const:
        X_fit = sm.add_constant(X_fit, has_constant='add')
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
            "model_obj": hac_results, # Store the HAC results object
            "params": params,
            "pvals_hac": pvals,
            "se_hac": ses,
            "r2": hac_results.rsquared,
            "r2_adj": hac_results.rsquared_adj,
            "n_obs": int(hac_results.nobs),
            "resid": hac_results.resid, # Residuals from HAC object
            "fittedvalues": hac_results.fittedvalues,
            "model_formula": f"{y_name} ~ {' + '.join(X_fit.columns)} (HAC lags={lags})"
        }
    except Exception as e:
        logging.error(f"OLS fitting failed for {y_name}: {e}", exc_info=True)
        return {"model_obj": None, "error": str(e)} # Return model_obj: None


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
    ols_results['monthly_base'] = {}
    ols_results['monthly_extended'] = {}
    ols_results['monthly_constrained'] = {} # For beta=2 check

    # Ensure required columns exist
    req_cols_monthly = ["log_marketcap", "log_active", "log_nasdaq", "log_gas", "price_usd", "supply"]
    if not all(col in monthly_df.columns for col in req_cols_monthly):
         missing = set(req_cols_monthly) - set(monthly_df.columns)
         logging.error(f"Monthly DataFrame missing required columns for OLS: {missing}")
         return ols_results # Return empty results

    # --- Monthly Baseline ---
    logging.info("Fitting Monthly Baseline OLS (log_marketcap ~ log_active)...")
    y_m = monthly_df["log_marketcap"]
    X_m_base = monthly_df[["log_active"]]
    res_m_base = fit_ols_hac(y_m, X_m_base, add_const=True, lags=12)
    ols_results['monthly_base'] = res_m_base

    if res_m_base.get("model_obj"):
        # Calculate Fair Value and RMSE for baseline
        try:
            p = res_m_base["params"]
            fv_log = p["const"] + p["log_active"] * monthly_df["log_active"]
            # Align index before division
            fv_log_aligned, supply_aligned = fv_log.align(monthly_df["supply"], join='inner')
            # Add fair value column to the DataFrame passed in
            monthly_df['fair_price_base'] = np.exp(fv_log_aligned) / supply_aligned

            # Align prices before RMSE calculation
            actual_price_aligned, fair_price_aligned = monthly_df["price_usd"].align(monthly_df["fair_price_base"], join='inner')
            valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()
            if valid_idx.sum() > 0:
                rmse_base = np.sqrt(mean_squared_error(actual_price_aligned[valid_idx], fair_price_aligned[valid_idx]))
                ols_results['monthly_base']["RMSE_USD"] = rmse_base
                logging.info(f"Monthly Base OLS: R2={res_m_base.get('r2', np.nan):.3f}, RMSE={rmse_base:.2f}")
            else:
                 ols_results['monthly_base']["RMSE_USD"] = np.nan
                 logging.warning("Could not calculate RMSE for monthly base OLS (no valid price pairs).")

        except Exception as e:
            logging.error(f"Error calculating fair value/RMSE for monthly base OLS: {e}")
            ols_results['monthly_base']["RMSE_USD"] = np.nan

    # --- Monthly Extended ---
    logging.info("Fitting Monthly Extended OLS (log_marketcap ~ log_active + log_nasdaq + log_gas)...")
    X_m_ext_cols = ["log_active", "log_nasdaq", "log_gas"]
    X_m_ext = monthly_df[X_m_ext_cols]
    res_m_ext = fit_ols_hac(y_m, X_m_ext, add_const=True, lags=12)
    ols_results['monthly_extended'] = res_m_ext

    if res_m_ext.get("model_obj"):
        # Calculate Fair Value and RMSE for extended
        try:
            p_ext = res_m_ext["params"]
            fv_log_ext = (p_ext["const"] +
                          p_ext["log_active"] * monthly_df["log_active"] +
                          p_ext["log_nasdaq"] * monthly_df["log_nasdaq"] +
                          p_ext["log_gas"] * monthly_df["log_gas"])

            fv_log_ext_aligned, supply_aligned = fv_log_ext.align(monthly_df["supply"], join='inner')
            # Add fair value column to the DataFrame passed in
            monthly_df['fair_price_ext'] = np.exp(fv_log_ext_aligned) / supply_aligned

            actual_price_aligned, fair_price_aligned = monthly_df["price_usd"].align(monthly_df["fair_price_ext"], join='inner')
            valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()

            if valid_idx.sum() > 0:
                rmse_ext = np.sqrt(mean_squared_error(actual_price_aligned[valid_idx], fair_price_aligned[valid_idx]))
                ols_results['monthly_extended']["RMSE_USD"] = rmse_ext
                logging.info(f"Monthly Extended OLS: R2={res_m_ext.get('r2', np.nan):.3f}, RMSE={rmse_ext:.2f}")
            else:
                 ols_results['monthly_extended']["RMSE_USD"] = np.nan
                 logging.warning("Could not calculate RMSE for monthly extended OLS (no valid price pairs).")

        except Exception as e:
            logging.error(f"Error calculating fair value/RMSE for monthly extended OLS: {e}")
            ols_results['monthly_extended']["RMSE_USD"] = np.nan

    # --- Monthly Constrained (Beta=2) ---
    if ols_results['monthly_base'].get("params"):
        try:
            alpha_hat = ols_results['monthly_base']["params"]["const"]
            beta_fixed = 2.0
            fv_log_constr = alpha_hat + beta_fixed * monthly_df["log_active"]

            fv_log_constr_aligned, supply_aligned = fv_log_constr.align(monthly_df["supply"], join='inner')
            # Add fair value column to the DataFrame passed in
            monthly_df["fair_price_constr"] = np.exp(fv_log_constr_aligned) / supply_aligned

            actual_price_aligned, fair_price_aligned = monthly_df["price_usd"].align(monthly_df["fair_price_constr"], join='inner')
            valid_idx = actual_price_aligned.notna() & fair_price_aligned.notna()

            if valid_idx.sum() > 0:
                rmse_c = np.sqrt(mean_squared_error(actual_price_aligned[valid_idx], fair_price_aligned[valid_idx]))
                ols_results["monthly_constrained"] = {
                    "alpha": alpha_hat, "beta": beta_fixed, "RMSE_USD": rmse_c
                }
                logging.info(f"Monthly Constrained (beta=2) OLS: RMSE={rmse_c:.2f}")
            else:
                 ols_results["monthly_constrained"] = {"alpha": alpha_hat, "beta": beta_fixed, "RMSE_USD": np.nan}
                 logging.warning("Could not calculate RMSE for monthly constrained OLS (no valid price pairs).")

        except Exception as e:
            logging.error(f"Error calculating fair value/RMSE for monthly constrained OLS: {e}")
            ols_results["monthly_constrained"] = {"RMSE_USD": np.nan}

    return ols_results


# --- Residual Diagnostics ---

def run_residual_diagnostics(ols_hac_results: dict) -> dict:
    """
    Performs residual diagnostics on a fitted OLS model (HAC results object).

    Args:
        ols_hac_results: The dictionary returned by fit_ols_hac.

    Returns:
        Dictionary containing diagnostic test results.
    """
    logging.info("Running Residual Diagnostics...")
    diag_results = {}
    fit = ols_hac_results.get("model_obj") # Get the HAC results object

    if fit is None or not hasattr(fit, 'resid') or not hasattr(fit, 'model'):
        logging.warning("Skipping diagnostics: Valid model fit object not found.")
        return diag_results

    resid = fit.resid
    # Exog might need to be reconstructed if add_constant was used
    # Let's try to get it from the underlying model if possible
    try:
        # Access the model attached to the results wrapper
        underlying_model = fit.model
        X = underlying_model.exog
        y = underlying_model.endog
        n_obs, k_vars = X.shape
    except Exception as e:
        logging.error(f"Could not retrieve exog/endog variables for diagnostics: {e}")
        return diag_results

    if len(resid) < 15 or len(resid) <= k_vars: # Need enough residuals
        logging.warning(f"Skipping diagnostics: Insufficient residuals ({len(resid)}).")
        return diag_results

    # Durbin-Watson
    try:
        dw = durbin_watson(resid)
        diag_results["DW"] = dw
        logging.info(f"  Durbin-Watson: {dw:.2f}")
    except Exception as e:
        logging.warning(f"Durbin-Watson test failed: {e}")
        diag_results["DW"] = np.nan

    # Breusch-Godfrey (Serial Correlation) - Use fit object directly
    try:
        # Use lags=min(12, n_obs // 4) or similar heuristic
        bg_lags = min(12, len(resid) // 4)
        if bg_lags > 0:
             # Need the original OLS fit, not HAC for this test typically
             # Refit OLS without HAC just for this diagnostic
             ols_fit_plain = sm.OLS(y, X).fit()
             _, bg_p, _, _ = acorr_breusch_godfrey(ols_fit_plain, nlags=bg_lags)
             diag_results["BG_p"] = bg_p
             logging.info(f"  Breusch-Godfrey (lags={bg_lags}): p={bg_p:.3f}")
        else:
             logging.warning("Skipping Breusch-Godfrey: not enough observations for lags.")
             diag_results["BG_p"] = np.nan
    except Exception as e:
        logging.warning(f"Breusch-Godfrey test failed: {e}")
        diag_results["BG_p"] = np.nan

    # Breusch-Pagan (Heteroskedasticity)
    try:
        _, bp_p, _, _ = het_breuschpagan(resid, X)
        diag_results["BP_p"] = bp_p
        logging.info(f"  Breusch-Pagan: p={bp_p:.3f}")
    except Exception as e:
        logging.warning(f"Breusch-Pagan test failed: {e}")
        diag_results["BP_p"] = np.nan

    # White Test (Heteroskedasticity)
    try:
        _, w_p, _, _ = het_white(resid, X)
        diag_results["White_p"] = w_p
        logging.info(f"  White Test: p={w_p:.3f}")
    except Exception as e:
        logging.warning(f"White test failed: {e}")
        diag_results["White_p"] = np.nan

    # Jarque-Bera (Normality)
    try:
        jb_stat, jb_p = jarque_bera(resid)
        diag_results["JB_p"] = jb_p
        logging.info(f"  Jarque-Bera: p={jb_p:.3f}")
    except Exception as e:
        logging.warning(f"Jarque-Bera test failed: {e}")
        diag_results["JB_p"] = np.nan

    return diag_results


# --- Structural Break Tests ---

def run_structural_break_tests(ols_hac_results: dict, break_dates: dict) -> dict:
    """
    Performs CUSUM and Chow tests for structural breaks.

    Args:
        ols_hac_results: The dictionary returned by fit_ols_hac.
        break_dates: Dictionary mapping test names (e.g., "EIP1559") to date strings.

    Returns:
        Dictionary containing structural break test results.
    """
    logging.info("Running Structural Break Tests...")
    break_results = {}
    fit = ols_hac_results.get("model_obj")

    if fit is None or not hasattr(fit, 'resid') or not hasattr(fit, 'model'):
        logging.warning("Skipping structural break tests: Valid model fit object not found.")
        return break_results

    resid = fit.resid
    # Need original endog/exog for Chow test refitting
    try:
        # Access the model attached to the results wrapper
        underlying_model = fit.model
        y_endog = underlying_model.endog
        X_exog = underlying_model.exog
        # Get original data index if possible (assuming it's stored)
        data_index = getattr(underlying_model.data, 'row_labels', pd.RangeIndex(len(y_endog)))
        if not isinstance(data_index, pd.DatetimeIndex):
             # If index isn't datetime, try converting or warn
             try:
                 data_index = pd.to_datetime(data_index)
             except Exception as idx_e:
                 logging.warning(f"Model data index is not datetime and conversion failed: {idx_e}. Chow test dates might be inaccurate.")

        n_obs, k_vars = X_exog.shape
    except Exception as e:
        logging.error(f"Could not retrieve model data for structural break tests: {e}")
        return break_results

    if n_obs < k_vars + 10: # Need enough observations
        logging.warning(f"Skipping structural break tests: Insufficient observations ({n_obs}).")
        return break_results

    # 1. CUSUM Test on OLS Residuals
    try:
        # CUSUM test might require the non-HAC residuals/fit
        ols_fit_plain = sm.OLS(y_endog, X_exog).fit()
        # Filter out warnings during CUSUM test if they occur
        with np.errstate(invalid='ignore'), warnings.catch_warnings():
            # Ensure warnings module is available here
            warnings.simplefilter("ignore", category=SpecificationWarning)
            warnings.simplefilter("ignore", category=RuntimeWarning) # Handle potential runtime warnings too
            cus_stat, cus_p, _ = breaks_cusumolsresid(ols_fit_plain.resid) # Use plain OLS resid
        break_results["CUSUM_p"] = cus_p
        logging.info(f"  CUSUM Test: p={cus_p:.3f}")
    except Exception as e:
        logging.warning(f"CUSUM test failed: {e}", exc_info=False) # Less verbose logging
        break_results["CUSUM_p"] = np.nan

    # 2. Chow Tests for specified dates
    try:
        ssr_full = sm.OLS(y_endog, X_exog).fit().ssr # SSR from full model
    except Exception as e:
        logging.error(f"Could not fit full model for Chow test SSR: {e}")
        return break_results # Cannot proceed with Chow if full model fails

    for name, date_str in break_dates.items():
        try:
            bp = pd.Timestamp(date_str)
            mask_pre = data_index < bp
            mask_post = data_index >= bp # Use >= for post period

            y_pre, X_pre = y_endog[mask_pre], X_exog[mask_pre]
            y_post, X_post = y_endog[mask_post], X_exog[mask_post]

            # Check if enough observations in both sub-periods
            if min(len(y_pre), len(y_post)) < k_vars + 1:
                logging.warning(f"Chow test for '{name}' ({date_str}): insufficient observations in sub-period(s). Pre: {len(y_pre)}, Post: {len(y_post)}, Vars: {k_vars}")
                break_results[f"Chow_{name}_p"] = np.nan
                continue

            ssr_pre = sm.OLS(y_pre, X_pre).fit().ssr
            ssr_post = sm.OLS(y_post, X_post).fit().ssr

            df_num = k_vars
            df_den = len(y_pre) + len(y_post) - 2 * k_vars
            if df_den <= 0:
                 logging.warning(f"Chow test for '{name}' ({date_str}): non-positive denominator degrees of freedom ({df_den}).")
                 break_results[f"Chow_{name}_p"] = np.nan
                 continue

            f_stat = ((ssr_full - (ssr_pre + ssr_post)) / df_num) / ((ssr_pre + ssr_post) / df_den)
            # Check for non-positive F-stat which can happen with perfect fit in subsamples
            if f_stat < 0: f_stat = 0
            p_val = 1 - f.cdf(f_stat, df_num, df_den)
            break_results[f"Chow_{name}_p"] = p_val
            logging.info(f"  Chow Test '{name}' ({date_str}): p={p_val:.3f}")

        except Exception as e:
            logging.warning(f"Chow test failed for '{name}' ({date_str}): {e}")
            break_results[f"Chow_{name}_p"] = np.nan

    return break_results


# --- VECM Analysis ---

def run_vecm_analysis(df_monthly: pd.DataFrame, endog_cols: list[str], exog_cols: list[str] | None = None,
                      max_lags: int = 6, coint_rank: int = 1, det_order: int = 0) -> dict:
    """
    Performs VECM estimation and Johansen test.

    Args:
        df_monthly: Monthly DataFrame containing all needed columns.
        endog_cols: List of endogenous variable names.
        exog_cols: List of exogenous variable names (optional).
        max_lags: Max lags for VAR order selection.
        coint_rank: Assumed cointegration rank for VECM.
        det_order: Deterministic order for Johansen test (-1: none, 0: const, 1: trend).

    Returns:
        Dictionary containing VECM results.
    """
    logging.info("Running VECM Analysis...")
    vecm_results = {}

    required_cols = endog_cols + (exog_cols if exog_cols else [])
    if not all(col in df_monthly.columns for col in required_cols):
         missing = set(required_cols) - set(df_monthly.columns)
         logging.error(f"Monthly DataFrame missing required columns for VECM: {missing}")
         return {"error": f"Missing columns: {missing}"}

    # Prepare data, drop NaNs
    joint_df = df_monthly[required_cols].replace([np.inf, -np.inf], np.nan).dropna()
    Y = joint_df[endog_cols]
    all_exog_cols_exist = all(col in joint_df.columns for col in exog_cols) if exog_cols else True # Check if all needed exog cols are present
    X = joint_df[exog_cols] if exog_cols and all_exog_cols_exist else None

    if len(Y) < max_lags + 10: # Need enough data
        logging.warning(f"Skipping VECM: Insufficient observations ({len(Y)}) after dropna.")
        return {"error": "Insufficient observations."}

    try:
        # 1. Lag Order Selection
        var_model = VAR(Y, exog=X)
        # Handle potential errors during lag selection
        try:
            selected_orders = var_model.select_order(maxlags=max_lags)
            aic_lag = selected_orders.aic if selected_orders.aic else 2 # Default lag
        except Exception as lag_e:
            logging.warning(f"VAR lag order selection failed: {lag_e}. Defaulting to lag 2.")
            aic_lag = 2

        k_ar_diff = max(aic_lag - 1, 1) # Lag for Johansen/VECM (k-1 convention)
        logging.info(f"  VAR lag order selected (AIC): {aic_lag} => k_ar_diff = {k_ar_diff}")
        vecm_results["var_aic_lag"] = aic_lag
        vecm_results["k_ar_diff"] = k_ar_diff

        # 2. Johansen Test (Optional but informative)
        try:
             jres = coint_johansen(Y, det_order=det_order, k_ar_diff=k_ar_diff)
             vecm_results["johansen_trace_stat"] = jres.lr1.tolist()
             vecm_results["johansen_crit_5pct"] = jres.cvt[:, 1].tolist()
             actual_rank = sum(jres.lr1 > jres.cvt[:, 1])
             logging.info(f"  Johansen Test suggests rank: {actual_rank} (Trace Stat > 5% Crit)")
             vecm_results["johansen_suggested_rank"] = actual_rank
        except Exception as johansen_e:
             logging.warning(f"Johansen test failed: {johansen_e}")
             vecm_results["johansen_suggested_rank"] = "Error"


        # 3. Fit VECM
        vecm = VECM(
            Y,
            exog=X,
            k_ar_diff=k_ar_diff,
            coint_rank=coint_rank, # Use pre-defined rank
            deterministic="ci" if det_order == 0 else ("li" if det_order == -1 else "co") # Match deterministic term
        )
        vecm_fit = vecm.fit()
        vecm_results["summary"] = vecm_fit.summary().as_text()

        # Extract key parameters (assuming rank=1 and specific variable order)
        if coint_rank == 1 and len(endog_cols) >= 2:
            try:
                # Beta (Cointegrating vector, normalized on first variable)
                # beta = [1, -beta_1/beta_0, -beta_2/beta_0, ...]
                if abs(vecm_fit.beta[0, 0]) > 1e-6: # Avoid division by zero
                    beta_norm = -vecm_fit.beta[1:, 0] / vecm_fit.beta[0, 0]
                    vecm_results["coint_vector_norm"] = [1.0] + beta_norm.tolist()
                    # Store specific beta for log_active if it's the second variable
                    if len(endog_cols) > 1 and endog_cols[1] == 'log_active':
                         vecm_results["beta_active_coint"] = beta_norm[0]
                else:
                    logging.warning("First element of beta vector is near zero. Cannot normalize.")
                    vecm_results["coint_vector_norm"] = "Normalization failed"

                # Alpha (Adjustment coefficients)
                vecm_results["alpha_coeffs"] = vecm_fit.alpha[:, 0].tolist()
                vecm_results["alpha_pvals"] = vecm_fit.pvalues_alpha[:, 0].tolist()
                # Store specific alpha for log_marketcap if it's the first variable
                if endog_cols[0] == 'log_marketcap':
                    vecm_results["alpha_mcap"] = vecm_fit.alpha[0, 0]
                    vecm_results["alpha_mcap_p"] = vecm_fit.pvalues_alpha[0, 0]
                if len(endog_cols) > 1 and endog_cols[1] == 'log_active':
                     vecm_results["alpha_active_p"] = vecm_fit.pvalues_alpha[1, 0] # Store p-value for active adjustment

            except Exception as e:
                logging.warning(f"Could not extract specific VECM parameters: {e}")

        logging.info("VECM fitting complete.")
        return vecm_results

    except Exception as e:
        logging.error(f"VECM analysis failed: {e}", exc_info=True)
        return {"error": str(e)}


# --- ARDL Analysis ---

def run_ardl_analysis(df_monthly: pd.DataFrame, endog_col: str, exog_cols: list[str],
                      max_lags: int = 6, trend: str = 'c') -> dict:
    """
    Performs ARDL estimation and bounds testing.

    Args:
        df_monthly: Monthly DataFrame.
        endog_col: Name of the endogenous variable.
        exog_cols: List of exogenous variable names.
        max_lags: Max lags for ARDL order selection (or fixed lags).
        trend: Trend specification ('n', 'c', 't', 'ct').

    Returns:
        Dictionary containing ARDL results.
    """
    logging.info("Running ARDL Analysis...")
    ardl_results = {}

    required_cols = [endog_col] + exog_cols
    if not all(col in df_monthly.columns for col in required_cols):
         missing = set(required_cols) - set(df_monthly.columns)
         logging.error(f"Monthly DataFrame missing required columns for ARDL: {missing}")
         return {"error": f"Missing columns: {missing}"}

    # Prepare data, drop NaNs
    joint_df = df_monthly[required_cols].replace([np.inf, -np.inf], np.nan).dropna()
    y = joint_df[endog_col]
    X = joint_df[exog_cols]

    if len(y) < max_lags + 10: # Need enough data
        logging.warning(f"Skipping ARDL: Insufficient observations ({len(y)}) after dropna.")
        return {"error": "Insufficient observations."}

    try:
        # Using fixed lags from original script for reproducibility
        p = 2
        order_q = {name: 1 for name in exog_cols}
        logging.info(f"Using fixed ARDL order: p={p}, q={order_q}")
        ardl_results["order_p"] = p
        ardl_results["order_q"] = order_q

        # 2. Fit ARDL Model
        model_ardl = ARDL(
            endog=y,
            lags=p,
            exog=X,
            order=order_q,
            trend=trend,
        )
        res_ardl = model_ardl.fit()
        ardl_results["summary"] = res_ardl.summary().as_text()

        # Extract ECT coefficient (coefficient of endog.L1)
        try:
            ect_coeff = res_ardl.params[f"{endog_col}.L1"]
            ardl_results["ect_coeff"] = float(ect_coeff)
            logging.info(f"  ARDL ECT coefficient ({endog_col}.L1): {ect_coeff:.3f}")
        except KeyError:
            logging.warning(f"Could not find ECT coefficient '{endog_col}.L1' in ARDL params.")
            ardl_results["ect_coeff"] = np.nan


        # 3. Run Bounds Test (Construct UECM directly)
        logging.info("  Constructing UECM for bounds testing...")
        try:
            # Determine case based on trend: case 1 (n), case 2 (c, restricted), case 3 (c, unrestricted), case 4 (t), case 5 (ct)
            trend_case_map = {'n': 1, 'c': 3, 't': 4, 'ct': 5} # Using unrestricted constant case 3 for 'c'
            bounds_case = trend_case_map.get(trend, 3)

            # Get lags from the fitted ARDL model
            ar_lags = res_ardl.ar_lags
            # Order dictionary might contain lags for exogenous variables
            # Need to construct the UECM order correctly
            uecm_lags = max(ar_lags) - 1 if ar_lags else 0 # Lag order for differenced endogenous terms
            uecm_order = {key: val for key, val in order_q.items()} # Lags for differenced exogenous terms

            uecm_model_manual = UECM(
                endog=y,
                lags=uecm_lags, # Lags for diff(endog)
                exog=X,
                order=uecm_order, # Lags for diff(exog)
                trend=trend
            )
            # Fit the UECM model
            res_uecm_manual = uecm_model_manual.fit()

            # Perform the bounds test on the fitted UECM
            bounds_test_result = res_uecm_manual.bounds_test(case=bounds_case) # Use case defined earlier

            stat = float(bounds_test_result.stat)
            # Access p-values safely
            p_upper = getattr(bounds_test_result, 'pu', np.nan)
            p_lower = getattr(bounds_test_result, 'pl', np.nan)

            ardl_results["bounds_stat"] = stat
            ardl_results["bounds_p_upper"] = p_upper
            ardl_results["bounds_p_lower"] = p_lower
            ardl_results["bounds_test_summary"] = str(bounds_test_result)

            cointegrated_5pct = p_lower < 0.05 if pd.notna(p_lower) else False
            ardl_results["cointegrated_5pct"] = cointegrated_5pct

            logging.info(f"  Bounds Test: F-stat={stat:.3f}, Lower p={p_lower:.3f}, Upper p={p_upper:.3f}")
            logging.info(f"  Cointegration at 5% (based on lower p): {cointegrated_5pct}")

        except AttributeError as ae:
             # This might catch the original 'dl_lags' error or others
             logging.error(f"Attribute error during manual UECM construction or bounds test: {ae}. Skipping bounds test.")
             ardl_results["bounds_stat"] = np.nan
             ardl_results["bounds_p_upper"] = np.nan
             ardl_results["bounds_p_lower"] = np.nan
             ardl_results["cointegrated_5pct"] = None
        except Exception as e_bounds:
             logging.error(f"Error during manual UECM construction or bounds test: {e_bounds}. Skipping bounds test.", exc_info=True)
             ardl_results["bounds_stat"] = np.nan
             ardl_results["bounds_p_upper"] = np.nan
             ardl_results["bounds_p_lower"] = np.nan
             ardl_results["cointegrated_5pct"] = None

        return ardl_results

    except Exception as e:
        logging.error(f"ARDL analysis failed: {e}", exc_info=True)
        return {"error": str(e)}


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