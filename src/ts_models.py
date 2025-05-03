# src/ts_models.py

import logging
import pandas as pd
import numpy as np
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen
from statsmodels.tsa.ardl import ARDL, UECM

# --- VECM Analysis ---


def run_vecm_analysis(
    df_monthly: pd.DataFrame,
    endog_cols: list[str],
    exog_cols: list[str] | None = None,
    max_lags: int = 6,
    coint_rank: int = 1,
    det_order: int = 0,
) -> dict:
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
    all_exog_cols_exist = (
        all(col in joint_df.columns for col in exog_cols) if exog_cols else True
    )  # Check if all needed exog cols are present
    X = joint_df[exog_cols] if exog_cols and all_exog_cols_exist else None

    if len(Y) < max_lags + 10:  # Need enough data
        logging.warning(
            f"Skipping VECM: Insufficient observations ({len(Y)}) after dropna."
        )
        return {"error": "Insufficient observations."}

    try:
        # 1. Lag Order Selection
        var_model = VAR(Y, exog=X)
        # Handle potential errors during lag selection
        try:
            selected_orders = var_model.select_order(maxlags=max_lags)
            aic_lag = selected_orders.aic if selected_orders.aic else 2  # Default lag
        except Exception as lag_e:
            logging.warning(
                f"VAR lag order selection failed: {lag_e}. Defaulting to lag 2."
            )
            aic_lag = 2

        # Correct calculation allowing k_ar_diff=0
        k_ar_diff = max(aic_lag - 1, 0)
        logging.info(
            f"  VAR lag order selected (AIC): {aic_lag} => k_ar_diff = {k_ar_diff}"
        )
        vecm_results["var_aic_lag"] = aic_lag
        vecm_results["k_ar_diff"] = k_ar_diff

        # 2. Johansen Test (Optional but informative)
        try:
            jres = coint_johansen(Y, det_order=det_order, k_ar_diff=k_ar_diff)
            vecm_results["johansen_trace_stat"] = jres.lr1.tolist()
            vecm_results["johansen_crit_5pct"] = jres.cvt[:, 1].tolist()
            actual_rank = sum(jres.lr1 > jres.cvt[:, 1])
            logging.info(
                f"  Johansen Test suggests rank: {actual_rank} (Trace Stat > 5% Crit)"
            )
            vecm_results["johansen_suggested_rank"] = actual_rank
        except Exception as johansen_e:
            logging.warning(f"Johansen test failed: {johansen_e}")
            vecm_results["johansen_suggested_rank"] = "Error"

        # 3. Fit VECM
        vecm = VECM(
            Y,
            exog=X,
            k_ar_diff=k_ar_diff,
            coint_rank=coint_rank,  # Use pre-defined rank
            deterministic="ci"
            if det_order == 0
            else ("li" if det_order == -1 else "co"),  # Match deterministic term
        )
        vecm_fit = vecm.fit()
        # Log the summary instead of printing
        logging.info(
            "\n--- VECM Fit Summary ---\n%s\n------------------------",
            vecm_fit.summary().as_text(),
        )
        vecm_results["summary"] = (
            vecm_fit.summary().as_text()
        )  # Keep summary in results dict

        # Extract key parameters (assuming rank=1 and specific variable order)
        if coint_rank == 1 and len(endog_cols) >= 2:
            try:
                # Beta (Cointegrating vector, normalized on first variable)
                # beta = [1, -beta_1/beta_0, -beta_2/beta_0, ...]
                if abs(vecm_fit.beta[0, 0]) > 1e-6:  # Avoid division by zero
                    beta_norm = -vecm_fit.beta[1:, 0] / vecm_fit.beta[0, 0]
                    vecm_results["coint_vector_norm"] = [1.0] + beta_norm.tolist()
                    # Store specific beta for log_active if it's the second variable
                    if len(endog_cols) > 1 and endog_cols[1] == "log_active":
                        vecm_results["beta_active_coint"] = beta_norm[0]
                else:
                    logging.warning(
                        "First element of beta vector is near zero. Cannot normalize."
                    )
                    vecm_results["coint_vector_norm"] = "Normalization failed"

                # Alpha (Adjustment coefficients)
                vecm_results["alpha_coeffs"] = vecm_fit.alpha[:, 0].tolist()
                vecm_results["alpha_pvals"] = vecm_fit.pvalues_alpha[:, 0].tolist()
                # Store specific alpha for log_marketcap if it's the first variable
                if endog_cols[0] == "log_marketcap":
                    vecm_results["alpha_mcap"] = vecm_fit.alpha[0, 0]
                    vecm_results["alpha_mcap_p"] = vecm_fit.pvalues_alpha[0, 0]
                if len(endog_cols) > 1 and endog_cols[1] == "log_active":
                    vecm_results["alpha_active_p"] = vecm_fit.pvalues_alpha[
                        1, 0
                    ]  # Store p-value for active adjustment

            except Exception as e:
                logging.warning(f"Could not extract specific VECM parameters: {e}")

        logging.info("VECM fitting complete.")
        return vecm_results

    except Exception as e:
        logging.error(f"VECM analysis failed: {e}", exc_info=True)
        return {"error": str(e)}


# --- ARDL Analysis ---


def run_ardl_analysis(
    df_monthly: pd.DataFrame,
    endog_col: str,
    exog_cols: list[str],
    max_lags: int = 6,
    trend: str = "c",
) -> dict:
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

    if len(y) < max_lags + 10:  # Need enough data
        logging.warning(
            f"Skipping ARDL: Insufficient observations ({len(y)}) after dropna."
        )
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
        # Log the summary instead of printing
        logging.info(
            "\n--- ARDL Fit Summary ---\n%s\n------------------------",
            res_ardl.summary().as_text(),
        )
        ardl_results["summary"] = (
            res_ardl.summary().as_text()
        )  # Keep summary in results dict

        # Extract ECT coefficient (coefficient of endog.L1)
        try:
            ect_coeff = res_ardl.params[f"{endog_col}.L1"]
            ardl_results["ect_coeff"] = float(ect_coeff)
            logging.info(f"  ARDL ECT coefficient ({endog_col}.L1): {ect_coeff:.3f}")
        except KeyError:
            logging.warning(
                f"Could not find ECT coefficient '{endog_col}.L1' in ARDL params."
            )
            ardl_results["ect_coeff"] = np.nan

        # 3. Run Bounds Test (Construct UECM directly)
        logging.info("  Constructing UECM for bounds testing...")
        try:
            # Determine case based on trend: case 1 (n), case 2 (c, restricted), case 3 (c, unrestricted), case 4 (t), case 5 (ct)
            trend_case_map = {
                "n": 1,
                "c": 3,
                "t": 4,
                "ct": 5,
            }  # Using unrestricted constant case 3 for 'c'
            bounds_case = trend_case_map.get(trend, 3)

            # Get lags from the fitted ARDL model
            ar_lags = res_ardl.ar_lags
            # Order dictionary might contain lags for exogenous variables
            # Need to construct the UECM order correctly
            uecm_lags = (
                max(ar_lags) - 1 if ar_lags else 0
            )  # Lag order for differenced endogenous terms
            uecm_order = {
                key: val for key, val in order_q.items()
            }  # Lags for differenced exogenous terms

            uecm_model_manual = UECM(
                endog=y,
                lags=uecm_lags,  # Lags for diff(endog)
                exog=X,
                order=uecm_order,  # Lags for diff(exog)
                trend=trend,
            )
            # Fit the UECM model
            res_uecm_manual = uecm_model_manual.fit()

            # Perform the bounds test on the fitted UECM
            bounds_test_result = res_uecm_manual.bounds_test(
                case=bounds_case
            )  # Use case defined earlier

            stat = float(bounds_test_result.stat)
            # Access p-values safely
            p_upper = getattr(bounds_test_result, "pu", np.nan)
            p_lower = getattr(bounds_test_result, "pl", np.nan)

            ardl_results["bounds_stat"] = stat
            ardl_results["bounds_p_upper"] = p_upper
            ardl_results["bounds_p_lower"] = p_lower
            # Log the bounds test summary instead of just storing it
            bounds_summary_text = str(bounds_test_result)
            logging.info(
                "\n--- ARDL Bounds Test Summary ---\n%s\n-----------------------------",
                bounds_summary_text,
            )
            ardl_results["bounds_test_summary"] = (
                bounds_summary_text  # Keep summary in results dict
            )

            cointegrated_5pct = p_lower < 0.05 if pd.notna(p_lower) else False
            ardl_results["cointegrated_5pct"] = cointegrated_5pct

            logging.info(
                f"  Bounds Test: F-stat={stat:.3f}, Lower p={p_lower:.3f}, Upper p={p_upper:.3f}"
            )
            logging.info(
                f"  Cointegration at 5% (based on lower p): {cointegrated_5pct}"
            )

        except AttributeError as ae:
            # This might catch the original 'dl_lags' error or others
            logging.error(
                f"Attribute error during manual UECM construction or bounds test: {ae}. Skipping bounds test."
            )
            ardl_results["bounds_stat"] = np.nan
            ardl_results["bounds_p_upper"] = np.nan
            ardl_results["bounds_p_lower"] = np.nan
            ardl_results["cointegrated_5pct"] = None
        except Exception as e_bounds:
            logging.error(
                f"Error during manual UECM construction or bounds test: {e_bounds}. Skipping bounds test.",
                exc_info=True,
            )
            ardl_results["bounds_stat"] = np.nan
            ardl_results["bounds_p_upper"] = np.nan
            ardl_results["bounds_p_lower"] = np.nan
            ardl_results["cointegrated_5pct"] = None

        return ardl_results

    except Exception as e:
        logging.error(f"ARDL analysis failed: {e}", exc_info=True)
        return {"error": str(e)}
