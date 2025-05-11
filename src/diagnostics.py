"""Model diagnostic tests for OLS regressions.

Includes functions for:
- Residual diagnostics (Durbin-Watson, Breusch-Godfrey, Breusch-Pagan, White, Jarque-Bera).
- Structural break tests (CUSUM, Chow).
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Dict  # Use Dict for explicit type hint

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import f, jarque_bera
from statsmodels.regression.linear_model import \
    OLSResults  # For model fit types
from statsmodels.stats.diagnostic import (acorr_breusch_godfrey,
                                          breaks_cusumolsresid,
                                          het_breuschpagan, het_white)
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tools.sm_exceptions import SpecificationWarning

# --- Residual Diagnostics ---


def run_residual_diagnostics(ols_hac_results: Dict[str, Any]) -> Dict[str, Any]:
    """Performs residual diagnostics on a fitted OLS model (HAC results object).

    Calculates Durbin-Watson, Breusch-Godfrey, Breusch-Pagan, White, and
    Jarque-Bera tests based on the residuals and exogenous variables from the
    provided OLS results dictionary.

    Args:
        ols_hac_results (Dict[str, Any]): The dictionary returned by fit_ols_hac
            (or similar OLS results dict), expected to contain the key 'model_obj'
            holding the statsmodels results wrapper object.

    Returns:
        Dict[str, Any]: Dictionary containing diagnostic test results (statistic or p-value).
                        Keys include 'DW', 'BG_p', 'BP_p', 'White_p', 'JB_p'.
                        Values will be np.nan if a test fails or cannot be run.
    """
    logging.info("Running Residual Diagnostics...")
    diag_results: Dict[str, Any] = {}
    # Use Any for fit object as it could be different wrapper types, but check attributes
    fit: Any | None = ols_hac_results.get("model_obj")

    if fit is None or not hasattr(fit, "resid") or not hasattr(fit, "model"):
        logging.warning("Skipping diagnostics: Valid model fit object not found.")
        return diag_results

    resid: pd.Series | np.ndarray = fit.resid
    # Exog might need to be reconstructed if add_constant was used
    # Let's try to get it from the underlying model if possible
    try:
        # Access the model attached to the results wrapper
        underlying_model: Any = fit.model  # Model type can vary
        X: pd.DataFrame | np.ndarray = underlying_model.exog
        y: pd.Series | np.ndarray = underlying_model.endog
        n_obs: int
        k_vars: int
        n_obs, k_vars = X.shape
    except (AttributeError, ValueError):
        logging.exception("Could not retrieve exog/endog variables for diagnostics")
        return diag_results

    if len(resid) < 15 or len(resid) <= k_vars:  # Need enough residuals
        logging.warning(f"Skipping diagnostics: Insufficient residuals ({len(resid)}).")
        return diag_results

    # Durbin-Watson
    try:
        dw: float = durbin_watson(resid)
        diag_results["DW"] = dw
        logging.info(f"  Durbin-Watson: {dw:.2f}")
    except Exception as e:
        logging.warning(f"Durbin-Watson test failed: {e}")
        diag_results["DW"] = np.nan

    # Breusch-Godfrey (Serial Correlation) - Use fit object directly
    try:
        # Use lags=min(12, n_obs // 4) or similar heuristic
        bg_lags: int = min(12, len(resid) // 4)
        if bg_lags > 0:
            # Need the original OLS fit, not HAC for this test typically
            # Refit OLS without HAC just for this diagnostic
            ols_fit_plain: OLSResults = sm.OLS(y, X).fit()
            lm_stat: float
            bg_p: float
            f_stat: float
            f_pvalue: float
            lm_stat, bg_p, f_stat, f_pvalue = acorr_breusch_godfrey(
                ols_fit_plain, nlags=bg_lags
            )
            diag_results["BG_p"] = bg_p
            logging.info(f"  Breusch-Godfrey (lags={bg_lags}): p={bg_p:.3f}")
        else:
            logging.warning(
                "Skipping Breusch-Godfrey: not enough observations for lags."
            )
            diag_results["BG_p"] = np.nan
    except Exception as e:
        logging.warning(f"Breusch-Godfrey test failed: {e}")
        diag_results["BG_p"] = np.nan

    # Breusch-Pagan (Heteroskedasticity)
    try:
        lm_stat, bp_p, f_stat, f_pvalue = het_breuschpagan(resid, X)
        diag_results["BP_p"] = bp_p
        logging.info(f"  Breusch-Pagan: p={bp_p:.3f}")
    except Exception as e:
        logging.warning(f"Breusch-Pagan test failed: {e}")
        diag_results["BP_p"] = np.nan

    # White Test (Heteroskedasticity)
    try:
        lm_stat, w_p, f_stat, f_pvalue = het_white(resid, X)
        diag_results["White_p"] = w_p
        logging.info(f"  White Test: p={w_p:.3f}")
    except Exception as e:
        logging.warning(f"White test failed: {e}")
        diag_results["White_p"] = np.nan

    # Jarque-Bera (Normality)
    try:
        jb_stat: float
        jb_p: float
        jb_stat, jb_p = jarque_bera(resid)
        diag_results["JB_p"] = jb_p
        logging.info(f"  Jarque-Bera: p={jb_p:.3f}")
    except Exception as e:
        logging.warning(f"Jarque-Bera test failed: {e}")
        diag_results["JB_p"] = np.nan

    return diag_results


# --- Structural Break Tests ---


def run_structural_break_tests(
    ols_hac_results: Dict[str, Any],
    break_dates: Dict[str, str],  # Dates should be strings
) -> Dict[str, Any]:
    """Performs CUSUM and Chow tests for structural breaks.

    Uses the underlying OLS model from the results dictionary to perform:
    1. CUSUM test on OLS residuals.
    2. Chow tests for each date specified in the break_dates dictionary.

    Args:
        ols_hac_results (Dict[str, Any]): The dictionary returned by fit_ols_hac
            (or similar), expected to contain 'model_obj'.
        break_dates (Dict[str, str]): Dictionary mapping test names (e.g., "EIP1559")
            to date strings in 'YYYY-MM-DD' format.

    Returns:
        Dict[str, Any]: Dictionary containing structural break test p-values.
                        Keys include 'CUSUM_p' and 'Chow_{name}_p' for each
                        name in break_dates. Values will be np.nan if a test
                        fails or cannot be run.
    """
    logging.info("Running Structural Break Tests...")
    break_results: Dict[str, Any] = {}
    fit: Any | None = ols_hac_results.get("model_obj")

    if fit is None or not hasattr(fit, "resid") or not hasattr(fit, "model"):
        logging.warning(
            "Skipping structural break tests: Valid model fit object not found."
        )
        return break_results

    # Need original endog/exog for Chow test refitting
    try:
        # Access the model attached to the results wrapper
        underlying_model: Any = fit.model
        y_endog: pd.Series | np.ndarray = underlying_model.endog
        X_exog: pd.DataFrame | np.ndarray = underlying_model.exog
        # Get original data index if possible (assuming it's stored)
        data_index: pd.Index | pd.RangeIndex = getattr(
            underlying_model.data, "row_labels", pd.RangeIndex(len(y_endog))
        )
        # Attempt conversion to DatetimeIndex for comparison
        if not isinstance(data_index, pd.DatetimeIndex):
            try:
                data_index = pd.to_datetime(data_index)
            except Exception as idx_e:
                logging.warning(
                    f"Model data index is not datetime and conversion failed: {idx_e}. Chow test dates might be inaccurate."
                )
                # Proceed with caution, comparison might fail later

        n_obs: int
        k_vars: int
        n_obs, k_vars = X_exog.shape
    except Exception as e:
        logging.error(f"Could not retrieve model data for structural break tests: {e}")
        return break_results

    if n_obs < k_vars + 10:  # Need enough observations
        logging.warning(
            f"Skipping structural break tests: Insufficient observations ({n_obs})."
        )
        return break_results

    # 1. CUSUM Test on OLS Residuals
    try:
        # CUSUM test might require the non-HAC residuals/fit
        ols_fit_plain: OLSResults = sm.OLS(y_endog, X_exog).fit()
        # Filter out warnings during CUSUM test if they occur
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            # Ensure warnings module is available here
            warnings.simplefilter("ignore", category=SpecificationWarning)
            warnings.simplefilter(
                "ignore", category=RuntimeWarning
            )  # Handle potential runtime warnings too
            cus_stat: float
            cus_p: float
            bounds: tuple[np.ndarray, np.ndarray]
            cus_stat, cus_p, bounds = breaks_cusumolsresid(
                ols_fit_plain.resid
            )  # Use plain OLS resid
        break_results["CUSUM_p"] = cus_p
        logging.info(f"  CUSUM Test: p={cus_p:.3f}")
    except Exception as e:
        logging.warning(
            f"CUSUM test failed: {e}", exc_info=False
        )  # Less verbose logging
        break_results["CUSUM_p"] = np.nan

    # 2. Chow Tests for specified dates
    try:
        ssr_full: float = sm.OLS(y_endog, X_exog).fit().ssr  # SSR from full model
    except Exception as e:
        logging.error(f"Could not fit full model for Chow test SSR: {e}")
        # If full model fails, can't do Chow tests that rely on it
        for name in break_dates:
            break_results[f"Chow_{name}_p"] = np.nan
        return break_results  # Return results collected so far (e.g., CUSUM)

    for name, date_str in break_dates.items():
        chow_key = f"Chow_{name}_p"
        try:
            bp = pd.Timestamp(date_str)
            # Ensure data_index is comparable with Timestamp
            if not isinstance(data_index, pd.DatetimeIndex):
                logging.warning(
                    f"Skipping Chow test for '{name}': data index is not DatetimeIndex."
                )
                break_results[chow_key] = np.nan
                continue

            mask_pre: pd.Series | np.ndarray = data_index < bp
            mask_post: pd.Series | np.ndarray = (
                data_index >= bp
            )  # Use >= for post period

            # Ensure masks are numpy arrays for boolean indexing if X/y are numpy
            if isinstance(X_exog, np.ndarray):
                mask_pre = np.asarray(mask_pre)
                mask_post = np.asarray(mask_post)

            y_pre, X_pre = y_endog[mask_pre], X_exog[mask_pre]
            y_post, X_post = y_endog[mask_post], X_exog[mask_post]

            # Check if enough observations in both sub-periods
            n_pre = X_pre.shape[0] if hasattr(X_pre, "shape") else len(X_pre)
            n_post = X_post.shape[0] if hasattr(X_post, "shape") else len(X_post)

            if min(n_pre, n_post) < k_vars + 1:
                logging.warning(
                    f"Chow test for '{name}' ({date_str}): insufficient observations in sub-period(s). Pre: {n_pre}, Post: {n_post}, Vars: {k_vars}"
                )
                break_results[chow_key] = np.nan
                continue

            ssr_pre: float = sm.OLS(y_pre, X_pre).fit().ssr
            ssr_post: float = sm.OLS(y_post, X_post).fit().ssr

            df_num: int = k_vars
            df_den: int = n_pre + n_post - 2 * k_vars
            if df_den <= 0:
                logging.warning(
                    f"Chow test for '{name}' ({date_str}): non-positive denominator degrees of freedom ({df_den})."
                )
                break_results[chow_key] = np.nan
                continue

            f_stat: float = ((ssr_full - (ssr_pre + ssr_post)) / df_num) / (
                (ssr_pre + ssr_post) / df_den
            )
            # Check for non-positive F-stat which can happen with perfect fit in subsamples
            if f_stat < 0:
                f_stat = 0.0  # Set to float
            p_val: float = 1.0 - f.cdf(f_stat, df_num, df_den)  # Ensure float
            break_results[chow_key] = p_val
            logging.info(f"  Chow Test '{name}' ({date_str}): p={p_val:.3f}")

        except Exception as e:
            logging.warning(f"Chow test failed for '{name}' ({date_str}): {e}")
            break_results[chow_key] = np.nan

    return break_results
