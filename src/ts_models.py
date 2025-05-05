"""Time series models (VECM, ARDL) for econometric analysis."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional  # Use specific types

import numpy as np
import pandas as pd

# Import specific statsmodels types for hinting
from statsmodels.tsa.api import VAR
from statsmodels.tsa.ardl import ARDL, UECM, BoundsTestResult, ARDLResults
from statsmodels.tsa.vector_ar.vecm import (
    VECM,
    JohansenTestResult,
    VECMResults,
    coint_johansen,
)

# --- VECM Analysis ---


def run_vecm_analysis(
    df_monthly: pd.DataFrame,
    endog_cols: List[str],
    exog_cols: Optional[List[str]] = None,  # Use Optional and correct type hint
    max_lags: int = 6,
    coint_rank: int = 1,
    det_order: int = 0,
) -> Dict[str, Any]:
    """Performs VECM estimation and Johansen cointegration test.

    Estimates a Vector Error Correction Model (VECM) for the specified endogenous
    variables, potentially including exogenous variables. Also performs the
    Johansen test to assess the cointegration rank.

    Args:
        df_monthly (pd.DataFrame): Monthly DataFrame containing all needed columns.
                                   NaNs/Infs will be dropped before analysis.
        endog_cols (List[str]): List of endogenous variable names.
        exog_cols (Optional[List[str]]): List of exogenous variable names. Defaults to None.
        max_lags (int): Maximum number of lags to consider for VAR order selection (AIC).
                        Defaults to 6.
        coint_rank (int): Assumed cointegration rank for VECM estimation. Defaults to 1.
        det_order (int): Deterministic trend order for Johansen test and VECM.
                         -1: no intercept or trend.
                         0: constant term (intercept).
                         1: linear trend.
                         Defaults to 0.

    Returns:
        Dict[str, Any]: Dictionary containing VECM results, including:
            - 'var_aic_lag' (int): Lag order selected by AIC for the underlying VAR.
            - 'k_ar_diff' (int): Lag order used for VECM (k_ar - 1).
            - 'johansen_trace_stat' (list[float] | str): Johansen trace statistics. "Error" on failure.
            - 'johansen_crit_5pct' (list[float] | str): 5% critical values for Johansen test. "Error" on failure.
            - 'johansen_suggested_rank' (int | str): Cointegration rank suggested by Johansen test. "Error" on failure.
            - 'summary' (str): Text summary of the fitted VECM model.
            - 'coint_vector_norm' (list[float] | str): Normalized cointegrating vector (if rank=1). "Normalization failed" on error.
            - 'beta_active_coint' (float | None): Specific coefficient for 'log_active' in coint. vector (if applicable).
            - 'alpha_coeffs' (list[float] | None): Adjustment coefficients (alpha).
            - 'alpha_pvals' (list[float] | None): P-values for alpha coefficients.
            - 'alpha_mcap' (float | None): Specific alpha for 'log_marketcap' (if applicable).
            - 'alpha_mcap_p' (float | None): P-value for 'log_marketcap' alpha.
            - 'alpha_active_p' (float | None): P-value for 'log_active' alpha (if applicable).
            - 'error' (str | None): Error message if analysis failed, else None.
    """
    logging.info("Running VECM Analysis...")
    vecm_results: Dict[str, Any] = {"error": None}  # Initialize with error: None

    required_cols = endog_cols + (exog_cols if exog_cols else [])
    if not all(col in df_monthly.columns for col in required_cols):
        missing = set(required_cols) - set(df_monthly.columns)
        msg = f"Monthly DataFrame missing required columns for VECM: {missing}"
        logging.error(msg)
        vecm_results["error"] = msg
        return vecm_results

    # Prepare data, drop NaNs
    try:
        joint_df = df_monthly[required_cols].replace([np.inf, -np.inf], np.nan).dropna()
        Y: pd.DataFrame = joint_df[endog_cols]
        X: Optional[pd.DataFrame] = None  # Initialize X as Optional DataFrame
        if exog_cols and all(col in joint_df.columns for col in exog_cols):
            X = joint_df[exog_cols]

        if len(Y) < max_lags + 10:  # Need enough data
            msg = f"Skipping VECM: Insufficient observations ({len(Y)}) after dropna."
            logging.warning(msg)
            vecm_results["error"] = "Insufficient observations."
            return vecm_results

    except Exception as data_prep_e:
        logging.error(f"Error preparing data for VECM: {data_prep_e}", exc_info=True)
        vecm_results["error"] = f"Data preparation error: {data_prep_e}"
        return vecm_results

    try:
        # 1. Lag Order Selection
        var_model = VAR(Y, exog=X)
        aic_lag: int = 2  # Default lag
        try:
            # selected_orders can be None if selection fails
            selected_orders = var_model.select_order(maxlags=max_lags)
            if selected_orders is not None and selected_orders.aic is not None:
                aic_lag = selected_orders.aic
            else:
                logging.warning(
                    "VAR lag order selection returned None or no AIC lag. Defaulting to lag 2."
                )
        except Exception as lag_e:
            logging.warning(
                f"VAR lag order selection failed: {lag_e}. Defaulting to lag 2."
            )
            # Keep default aic_lag = 2

        k_ar_diff: int = max(aic_lag - 1, 0)
        logging.info(
            f"  VAR lag order selected (AIC): {aic_lag} => k_ar_diff = {k_ar_diff}"
        )
        vecm_results["var_aic_lag"] = aic_lag
        vecm_results["k_ar_diff"] = k_ar_diff

        # 2. Johansen Test (Optional but informative)
        try:
            # det_order: -1 constant=False, 0 constant=True, 1 constant=True trend=True
            jres: JohansenTestResult = coint_johansen(
                Y, det_order=det_order, k_ar_diff=k_ar_diff
            )
            vecm_results["johansen_trace_stat"] = jres.lr1.tolist()
            vecm_results["johansen_crit_5pct"] = jres.cvt[:, 1].tolist()
            # Ensure comparison is valid before summing
            valid_comparison = (
                (jres.lr1 > jres.cvt[:, 1])
                & np.isfinite(jres.lr1)
                & np.isfinite(jres.cvt[:, 1])
            )
            actual_rank: int = int(np.sum(valid_comparison))  # Cast sum to int
            logging.info(
                f"  Johansen Test suggests rank: {actual_rank} (Trace Stat > 5% Crit)"
            )
            vecm_results["johansen_suggested_rank"] = actual_rank
        except Exception as johansen_e:
            logging.warning(f"Johansen test failed: {johansen_e}")
            vecm_results["johansen_trace_stat"] = "Error"
            vecm_results["johansen_crit_5pct"] = "Error"
            vecm_results["johansen_suggested_rank"] = "Error"

        # 3. Fit VECM
        # Map det_order to deterministic string
        deterministic_terms: str
        if det_order == -1:
            deterministic_terms = "li"  # linear trend in CE only (no constant) - check statsmodels doc if this is intended
        elif det_order == 0:
            deterministic_terms = "ci"  # constant in CE only
        elif det_order == 1:
            deterministic_terms = "co"  # constant in CE and VAR
        else:
            logging.warning(f"Invalid det_order {det_order}. Defaulting to 'ci'.")
            deterministic_terms = "ci"

        vecm_model: VECM = VECM(
            Y,
            exog=X,
            k_ar_diff=k_ar_diff,
            coint_rank=coint_rank,
            deterministic=deterministic_terms,
        )
        vecm_fit: VECMResults = vecm_model.fit()
        # Log the summary instead of printing
        summary_text = vecm_fit.summary().as_text()
        logging.info(
            "\n--- VECM Fit Summary ---\n%s\n------------------------",
            summary_text,
        )
        vecm_results["summary"] = summary_text

        # Extract key parameters (assuming rank=1 and specific variable order)
        vecm_results["coint_vector_norm"] = None
        vecm_results["beta_active_coint"] = None
        vecm_results["alpha_coeffs"] = None
        vecm_results["alpha_pvals"] = None
        vecm_results["alpha_mcap"] = None
        vecm_results["alpha_mcap_p"] = None
        vecm_results["alpha_active_p"] = None

        if coint_rank == 1 and len(endog_cols) >= 2:
            try:
                # Beta (Cointegrating vector, normalized on first variable)
                beta_matrix = vecm_fit.beta
                if beta_matrix.shape[0] > 0 and abs(beta_matrix[0, 0]) > 1e-6:
                    beta_norm = -beta_matrix[1:, 0] / beta_matrix[0, 0]
                    vecm_results["coint_vector_norm"] = [1.0] + beta_norm.tolist()
                    if len(endog_cols) > 1 and endog_cols[1] == "log_active":
                        vecm_results["beta_active_coint"] = beta_norm[0]
                else:
                    logging.warning(
                        "First element of beta vector is near zero or beta vector empty. Cannot normalize."
                    )
                    vecm_results["coint_vector_norm"] = "Normalization failed"

                # Alpha (Adjustment coefficients)
                alpha_matrix = vecm_fit.alpha
                alpha_pvals_matrix = vecm_fit.pvalues_alpha
                if alpha_matrix.shape[1] > 0:  # Ensure alpha exists
                    vecm_results["alpha_coeffs"] = alpha_matrix[:, 0].tolist()
                    vecm_results["alpha_pvals"] = alpha_pvals_matrix[:, 0].tolist()
                    if endog_cols[0] == "log_marketcap":
                        vecm_results["alpha_mcap"] = alpha_matrix[0, 0]
                        vecm_results["alpha_mcap_p"] = alpha_pvals_matrix[0, 0]
                    if len(endog_cols) > 1 and endog_cols[1] == "log_active":
                        # Check index bounds before accessing
                        if alpha_pvals_matrix.shape[0] > 1:
                            vecm_results["alpha_active_p"] = alpha_pvals_matrix[1, 0]

            except (AttributeError, IndexError, TypeError, ValueError) as param_e:
                logging.warning(
                    f"Could not extract specific VECM parameters: {param_e}"
                )

        logging.info("VECM fitting complete.")
        return vecm_results

    except Exception as e:
        logging.error(f"VECM analysis failed: {e}", exc_info=True)
        vecm_results["error"] = str(e)
        return vecm_results


# --- ARDL Analysis ---


def run_ardl_analysis(
    df_monthly: pd.DataFrame,
    endog_col: str,
    exog_cols: List[str],
    max_lags: int = 6,  # Keep for signature, even if using fixed lags below
    trend: str = "c",
) -> Dict[str, Any]:
    """Performs ARDL estimation and bounds testing for cointegration.

    Estimates an Autoregressive Distributed Lag (ARDL) model and performs
    the Pesaran, Shin, and Smith (2001) bounds test to check for cointegration
    between the endogenous variable and exogenous variables. Uses fixed lags
    (p=2, q=1 for all exog) for reproducibility based on original script.

    Args:
        df_monthly (pd.DataFrame): Monthly DataFrame containing endogenous and
                                   exogenous variables. NaNs/Infs dropped.
        endog_col (str): Name of the endogenous variable column.
        exog_cols (List[str]): List of exogenous variable column names.
        max_lags (int): Maximum lags (kept for signature consistency, but fixed
                        lags p=2, q=1 are used internally). Defaults to 6.
        trend (str): Trend specification for the model ('n', 'c', 't', 'ct').
                     Defaults to 'c' (constant).

    Returns:
        Dict[str, Any]: Dictionary containing ARDL results, including:
            - 'order_p' (int): Autoregressive lag order used (fixed at 2).
            - 'order_q' (Dict[str, int]): Exogenous lag orders used (fixed at 1).
            - 'summary' (str): Text summary of the fitted ARDL model.
            - 'ect_coeff' (float | np.nan): Estimated error correction term coefficient. NaN on error.
            - 'bounds_stat' (float | np.nan): F-statistic from the bounds test. NaN on error.
            - 'bounds_p_upper' (float | np.nan): Upper bound p-value from bounds test. NaN on error.
            - 'bounds_p_lower' (float | np.nan): Lower bound p-value from bounds test. NaN on error.
            - 'bounds_test_summary' (str | None): Text summary of the bounds test result. None on error.
            - 'cointegrated_5pct' (bool | None): True if cointegrated at 5% based on lower p-value,
                                                False if not, None if test inconclusive or failed.
            - 'error' (str | None): Error message if analysis failed, else None.
    """
    logging.info("Running ARDL Analysis...")
    ardl_results: Dict[str, Any] = {"error": None}  # Initialize

    required_cols = [endog_col] + exog_cols
    if not all(col in df_monthly.columns for col in required_cols):
        missing = set(required_cols) - set(df_monthly.columns)
        msg = f"Monthly DataFrame missing required columns for ARDL: {missing}"
        logging.error(msg)
        ardl_results["error"] = msg
        return ardl_results

    # Prepare data, drop NaNs
    try:
        joint_df = df_monthly[required_cols].replace([np.inf, -np.inf], np.nan).dropna()
        y: pd.Series = joint_df[endog_col]
        X: pd.DataFrame = joint_df[exog_cols]

        # Use max_lags from signature for check, even if fixed lags used later
        if len(y) < max_lags + 10:
            msg = f"Skipping ARDL: Insufficient observations ({len(y)}) after dropna."
            logging.warning(msg)
            ardl_results["error"] = "Insufficient observations."
            return ardl_results

    except Exception as data_prep_e:
        logging.error(f"Error preparing data for ARDL: {data_prep_e}", exc_info=True)
        ardl_results["error"] = f"Data preparation error: {data_prep_e}"
        return ardl_results

    try:
        # Using fixed lags from original script for reproducibility
        p: int = 2
        order_q: Dict[str, int] = {name: 1 for name in exog_cols}
        logging.info(f"Using fixed ARDL order: p={p}, q={order_q}")
        ardl_results["order_p"] = p
        ardl_results["order_q"] = order_q

        # 2. Fit ARDL Model
        model_ardl: ARDL = ARDL(
            endog=y,
            lags=p,
            exog=X,
            order=order_q,
            trend=trend,
            # causal=True # Consider adding if appropriate for interpretation
        )
        res_ardl: ARDLResults = model_ardl.fit()
        summary_text = res_ardl.summary().as_text()
        logging.info(
            "\n--- ARDL Fit Summary ---\n%s\n------------------------",
            summary_text,
        )
        ardl_results["summary"] = summary_text

        # Extract ECT coefficient (coefficient of endog.L1)
        ardl_results["ect_coeff"] = np.nan  # Default
        try:
            ect_param_name = f"{endog_col}.L1"
            if ect_param_name in res_ardl.params.index:
                ect_coeff = res_ardl.params[ect_param_name]
                ardl_results["ect_coeff"] = float(ect_coeff)
                logging.info(
                    f"  ARDL ECT coefficient ({ect_param_name}): {ect_coeff:.3f}"
                )
            else:
                logging.warning(
                    f"Could not find ECT coefficient '{ect_param_name}' in ARDL params."
                )

        except (KeyError, ValueError, TypeError) as ect_e:
            logging.warning(f"Could not extract ECT coefficient: {ect_e}")

        # 3. Run Bounds Test (Construct UECM directly)
        logging.info("  Constructing UECM for bounds testing...")
        ardl_results["bounds_stat"] = np.nan
        ardl_results["bounds_p_upper"] = np.nan
        ardl_results["bounds_p_lower"] = np.nan
        ardl_results["bounds_test_summary"] = None
        ardl_results["cointegrated_5pct"] = None
        try:
            # Determine case based on trend
            trend_case_map: Dict[str, int] = {"n": 1, "c": 3, "t": 4, "ct": 5}
            bounds_case: int = trend_case_map.get(
                trend, 3
            )  # Default to case 3 (unrestricted constant)

            # Get lags from the fitted ARDL model
            ar_lags: List[int] = (
                res_ardl.ar_lags if res_ardl.ar_lags is not None else []
            )
            uecm_lags: int = max(ar_lags) - 1 if ar_lags else 0
            # Ensure order_q is used correctly for UECM exog lags
            uecm_order: Dict[str, int] = {key: val for key, val in order_q.items()}

            uecm_model_manual: UECM = UECM(
                endog=y,
                lags=uecm_lags,
                exog=X,
                order=uecm_order,
                trend=trend,
            )
            res_uecm_manual: ARDLResults = uecm_model_manual.fit()

            # Perform the bounds test
            bounds_test_result: BoundsTestResult = res_uecm_manual.bounds_test(
                case=bounds_case
            )

            # --- More Robust p-value extraction ---
            stat: float = np.nan
            p_upper: float = np.nan
            p_lower: float = np.nan
            bounds_summary_text: str = (
                "Bounds test failed or returned unexpected format."
            )

            try:
                stat = float(bounds_test_result.stat)  # Ensure float
                # Try direct attribute access
                p_upper_raw = bounds_test_result.pu
                p_lower_raw = bounds_test_result.pl
                # Attempt conversion to float, keep nan if conversion fails or attribute missing
                p_upper = float(p_upper_raw) if pd.notna(p_upper_raw) else np.nan
                p_lower = float(p_lower_raw) if pd.notna(p_lower_raw) else np.nan
                bounds_summary_text = str(
                    bounds_test_result
                )  # Get summary if successful
            except (AttributeError, ValueError, TypeError) as pval_err:
                logging.warning(
                    f"Could not extract bounds test p-values directly: {pval_err}"
                )
                # Fallback: Try parsing from summary string if direct access fails
                try:
                    summary_lines = str(bounds_test_result).splitlines()
                    for line in summary_lines:
                        if "Upper P-value:" in line:
                            p_upper = float(line.split(":")[1].strip())
                        elif "Lower P-value:" in line:
                            p_lower = float(line.split(":")[1].strip())
                    bounds_summary_text = str(
                        bounds_test_result
                    )  # Still use original summary if parsing works
                except Exception as parse_err:
                    logging.error(
                        f"Could not parse p-values from bounds test summary string: {parse_err}"
                    )
                    p_upper = np.nan  # Ensure they remain NaN if parsing fails
                    p_lower = np.nan
            # --- End More Robust extraction ---

            ardl_results["bounds_stat"] = stat
            ardl_results["bounds_p_upper"] = p_upper
            ardl_results["bounds_p_lower"] = p_lower

            logging.info(
                "\n--- ARDL Bounds Test Summary ---\n%s\n-----------------------------",
                bounds_summary_text,  # Log the potentially updated summary text
            )
            ardl_results["bounds_test_summary"] = bounds_summary_text

            # Determine cointegration based on the potentially NaN p_lower
            cointegrated_5pct: Optional[bool] = None
            # Only proceed if p_lower is a valid number
            if pd.notna(p_lower):
                if p_lower < 0.05:
                    cointegrated_5pct = True
                else:  # p_lower >= 0.05
                    cointegrated_5pct = False
            # If p_lower is NaN, cointegrated_5pct remains None

            ardl_results["cointegrated_5pct"] = cointegrated_5pct

            logging.info(
                f"  Bounds Test: F-stat={stat:.3f}, Lower p={p_lower:.3f}, Upper p={p_upper:.3f}"
            )
            logging.info(
                f"  Cointegration at 5% (based on lower p): {cointegrated_5pct}"
            )

        except AttributeError as ae:
            logging.error(
                f"Attribute error during UECM construction or bounds test: {ae}. Skipping bounds test."
            )
        except Exception as e_bounds:
            logging.error(
                f"Error during UECM construction or bounds test: {e_bounds}. Skipping bounds test.",
                exc_info=True,
            )

        return ardl_results

    except Exception as e:
        logging.error(f"ARDL analysis failed: {e}", exc_info=True)
        ardl_results["error"] = str(e)
        return ardl_results
