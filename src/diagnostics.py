# src/diagnostics.py

import logging
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.diagnostic import (
    acorr_breusch_godfrey,
    het_breuschpagan,
    het_white,
    breaks_cusumolsresid,
)
from statsmodels.tools.sm_exceptions import SpecificationWarning
from scipy.stats import jarque_bera, f
import warnings
from typing import Any

# --- Residual Diagnostics ---


def run_residual_diagnostics(ols_hac_results: dict[str, Any]) -> dict[str, Any]:
    """
    Performs residual diagnostics on a fitted OLS model (HAC results object).

    Args:
        ols_hac_results: The dictionary returned by fit_ols_hac (or similar OLS results dict).

    Returns:
        Dictionary containing diagnostic test results.
    """
    logging.info("Running Residual Diagnostics...")
    diag_results: dict[str, Any] = {}
    fit = ols_hac_results.get("model_obj")  # Get the HAC results object

    if fit is None or not hasattr(fit, "resid") or not hasattr(fit, "model"):
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
    except (AttributeError, ValueError):
        logging.exception("Could not retrieve exog/endog variables for diagnostics")
        return diag_results

    if len(resid) < 15 or len(resid) <= k_vars:  # Need enough residuals
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
            logging.warning(
                "Skipping Breusch-Godfrey: not enough observations for lags."
            )
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


def run_structural_break_tests(
    ols_hac_results: dict[str, Any],
    break_dates: dict[str, Any],
) -> dict[str, Any]:
    """
    Performs CUSUM and Chow tests for structural breaks.

    Args:
        ols_hac_results: The dictionary returned by fit_ols_hac (or similar).
        break_dates: Dictionary mapping test names (e.g., "EIP1559") to date strings.

    Returns:
        Dictionary containing structural break test results.
    """
    logging.info("Running Structural Break Tests...")
    break_results: dict[str, Any] = {}
    fit = ols_hac_results.get("model_obj")

    if fit is None or not hasattr(fit, "resid") or not hasattr(fit, "model"):
        logging.warning(
            "Skipping structural break tests: Valid model fit object not found."
        )
        return break_results

    # Need original endog/exog for Chow test refitting
    try:
        # Access the model attached to the results wrapper
        underlying_model = fit.model
        y_endog = underlying_model.endog
        X_exog = underlying_model.exog
        # Get original data index if possible (assuming it's stored)
        data_index = getattr(
            underlying_model.data, "row_labels", pd.RangeIndex(len(y_endog))
        )
        if not isinstance(data_index, pd.DatetimeIndex):
            # If index isn't datetime, try converting or warn
            try:
                data_index = pd.to_datetime(data_index)
            except Exception as idx_e:
                logging.warning(
                    f"Model data index is not datetime and conversion failed: {idx_e}. Chow test dates might be inaccurate."
                )

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
        ols_fit_plain = sm.OLS(y_endog, X_exog).fit()
        # Filter out warnings during CUSUM test if they occur
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            # Ensure warnings module is available here
            warnings.simplefilter("ignore", category=SpecificationWarning)
            warnings.simplefilter(
                "ignore", category=RuntimeWarning
            )  # Handle potential runtime warnings too
            cus_stat, cus_p, _ = breaks_cusumolsresid(
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
        ssr_full = sm.OLS(y_endog, X_exog).fit().ssr  # SSR from full model
    except Exception as e:
        logging.error(f"Could not fit full model for Chow test SSR: {e}")
        return break_results  # Cannot proceed with Chow if full model fails

    for name, date_str in break_dates.items():
        try:
            bp = pd.Timestamp(date_str)
            mask_pre = data_index < bp
            mask_post = data_index >= bp  # Use >= for post period

            y_pre, X_pre = y_endog[mask_pre], X_exog[mask_pre]
            y_post, X_post = y_endog[mask_post], X_exog[mask_post]

            # Check if enough observations in both sub-periods
            if min(len(y_pre), len(y_post)) < k_vars + 1:
                logging.warning(
                    f"Chow test for '{name}' ({date_str}): insufficient observations in sub-period(s). Pre: {len(y_pre)}, Post: {len(y_post)}, Vars: {k_vars}"
                )
                break_results[f"Chow_{name}_p"] = np.nan
                continue

            ssr_pre = sm.OLS(y_pre, X_pre).fit().ssr
            ssr_post = sm.OLS(y_post, X_post).fit().ssr

            df_num = k_vars
            df_den = len(y_pre) + len(y_post) - 2 * k_vars
            if df_den <= 0:
                logging.warning(
                    f"Chow test for '{name}' ({date_str}): non-positive denominator degrees of freedom ({df_den})."
                )
                break_results[f"Chow_{name}_p"] = np.nan
                continue

            f_stat = ((ssr_full - (ssr_pre + ssr_post)) / df_num) / (
                (ssr_pre + ssr_post) / df_den
            )
            # Check for non-positive F-stat which can happen with perfect fit in subsamples
            if f_stat < 0:
                f_stat = 0
            p_val = 1 - f.cdf(f_stat, df_num, df_den)
            break_results[f"Chow_{name}_p"] = p_val
            logging.info(f"  Chow Test '{name}' ({date_str}): p={p_val:.3f}")

        except Exception as e:
            logging.warning(f"Chow test failed for '{name}' ({date_str}): {e}")
            break_results[f"Chow_{name}_p"] = np.nan

    return break_results
