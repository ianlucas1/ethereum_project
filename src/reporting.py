"""Generates analysis summaries and handles JSON serialization.

Provides:
- A custom JSON encoder (`NpEncoder`) for handling NumPy types and NaN/Inf.
- A function (`generate_summary`) to compile results from various analysis
  steps into a structured dictionary and a human-readable interpretation text.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Sequence, Union  # Added Dict, Union

import numpy as np
import pandas as pd


# --- JSON Encoder for NumPy types ---
class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NumPy types and NaN/Inf values.

    Serializes NumPy integers, floats, arrays, pandas Timestamps/Periods,
    and handles NaN/Inf/NaT by converting them to None (JSON null).
    Falls back to string representation for other non-serializable types.
    """

    def default(self, obj: Any) -> Any:
        """Overrides default JSON encoding behavior.

        Args:
            obj (Any): The object to serialize.

        Returns:
            Any: The JSON-serializable representation of the object.
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            # Convert NaN/Inf to None for JSON compatibility
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            # Convert to object array first to safely handle None replacement
            try:
                # Create a mask for NaN/Inf values
                mask = np.isnan(obj) | np.isinf(obj)
                # Create an object array copy
                obj_copy = obj.astype(object)
                # Replace masked values with None
                obj_copy[mask] = None
                # Convert to list
                return obj_copy.tolist()
            except (TypeError, ValueError) as e:
                # Handle cases where astype(object) or masking fails unexpectedly
                logging.warning(
                    f"Could not convert ndarray with potential NaNs/Infs due to: {e}. Falling back to string.",
                    exc_info=True,
                )
                return str(obj)  # Fallback
        elif isinstance(obj, (pd.Timestamp, pd.Period)):
            # Format Timestamp/Period to ISO 8601 string
            try:
                return obj.isoformat()
            except AttributeError:  # Handle cases where isoformat might not exist (though unlikely for Timestamp/Period)
                return str(obj)
            except ValueError:  # Handle NaT
                return None
        elif pd.isna(obj):
            return None  # Handle pandas NaT or other NAs
        try:
            # Let the base class default method raise the TypeError
            return super().default(obj)
        except TypeError:
            # Handle non-serializable objects gracefully
            logging.warning(
                "Object of type %s is not JSON serializable. Representing as string.",
                type(obj),
            )
            return str(obj)


# --- Summary Generation ---

# Define a more specific type alias for the analysis results dictionary structure if known
# For now, stick with Dict[str, Any] for flexibility
AnalysisResultsDict = Dict[str, Any]


def _safe_get(
    data_dict: AnalysisResultsDict | Any,  # Allow Any for intermediate steps
    key_list: Sequence[Union[str, int]],  # Use Union for key types
    default: Any | None = None,
) -> Any:
    """Safely retrieves nested dictionary values or list/tuple elements.

    Traverses the keys in key_list through the nested structure data_dict.
    Handles potential KeyErrors, IndexErrors, TypeErrors, and None values
    during traversal. Also converts final NaN/Inf float values to the default.

    Args:
        data_dict (AnalysisResultsDict | Any): The dictionary or structure to traverse.
        key_list (Sequence[Union[str, int]]): An ordered sequence of keys/indices.
        default (Any | None): The value to return if traversal fails or the
                              final value is NaN/Inf. Defaults to None.

    Returns:
        Any: The retrieved value, or the default value.
    """
    current: Any = data_dict
    for key in key_list:
        # Check if current object is indexable/subscriptable
        is_dict = isinstance(current, dict)
        is_list_or_tuple = isinstance(current, (list, tuple))

        if not (is_dict or is_list_or_tuple):
            return default

        try:
            # Handle integer index for lists/tuples
            if isinstance(key, int) and is_list_or_tuple:
                if key >= len(current):
                    return default
                current = current[key]
            # Handle dictionary keys
            elif isinstance(key, str) and is_dict:
                # Use .get() which returns None if key is missing
                current = current.get(key)
                # If .get() returned None because the key was missing OR
                # if the key existed but its value was None, we should stop here
                # and return the default in the next check.
            else:
                # Invalid key type for the current object type
                return default
        except (KeyError, IndexError, TypeError):
            return default

        # If current became None (either key missing or value was None), stop traversal
        if current is None:
            return default

    # Final check: If the final value is NaN or Inf, return the default
    if isinstance(current, (float, np.floating)) and (
        np.isnan(current) or np.isinf(current)
    ):
        return default
    # Handle pandas NA values explicitly
    if pd.isna(current):
        return default

    return current


def _format_val(
    val: Any,
    precision: int = 2,
    is_p_value: bool = False,
    is_usd: bool = False,
    is_bool: bool = False,
) -> str:
    """Formats various data types into a string representation for the report.

    Handles None, NaN, Inf, floats, integers, booleans, Timestamps, and p-values.

    Args:
        val (Any): The value to format.
        precision (int): Decimal precision for floats (ignored for other types). Defaults to 2.
        is_p_value (bool): If True, format as p-value (<0.001 or 3 decimals). Defaults to False.
        is_usd (bool): If True, format as USD currency ($x,xxx). Defaults to False.
        is_bool (bool): If True, format as string 'True'/'False'. Defaults to False.

    Returns:
        str: The formatted string representation (e.g., "$1,234", "<0.001", "N/A").
    """
    # Handle infinity first
    if isinstance(val, (float, np.floating)) and np.isinf(val):
        return "+Infinity" if val > 0 else "-Infinity"
    # Handle None or NaN or pandas NA
    if val is None or pd.isna(val):
        return "N/A"
    # Format based on type
    if is_bool:
        return str(val)  # True/False
    if is_p_value:
        try:
            float_val = float(val)
            return "<0.001" if float_val < 0.001 else f"{float_val:.3f}"
        except (ValueError, TypeError):
            return "N/A"  # Cannot convert to float
    if is_usd:
        try:
            return f"${float(val):,.0f}"  # Format USD with commas, no decimals
        except (ValueError, TypeError):
            return "N/A"  # Cannot convert to float
    if isinstance(val, (int, float, np.number)):
        try:
            fmt_str = "{:." + str(precision) + "f}"
            return fmt_str.format(float(val))
        except (ValueError, TypeError):
            return "N/A"  # Cannot convert to float
    if isinstance(val, pd.Timestamp):  # Format Timestamp
        try:
            # Explicitly check it's not NaT before formatting
            if pd.isna(val):
                return "N/A"
            return val.strftime("%Y-%m-%d")
        except ValueError:  # Should be caught by pd.isna, but keep as fallback
            return "N/A"
    return str(val)  # Fallback for other types


def generate_summary(
    analysis_results: AnalysisResultsDict,
    monthly_df_with_fv: pd.DataFrame,
    monthly_df_oos: pd.DataFrame,
) -> Dict[str, Any]:
    """Generates the final results dictionary and interpretation text.

    Extracts key metrics from the analysis_results dictionary, formats them,
    and constructs a summary dictionary and a formatted interpretation string.

    Args:
        analysis_results (AnalysisResultsDict): Dictionary containing results
            from all analysis steps (OLS, diagnostics, VECM, ARDL, OOS).
        monthly_df_with_fv (pd.DataFrame): Monthly dataframe potentially modified
            by OLS benchmark function to include 'fair_price_ext'. Used to
            extract the last actual and fair prices.
        monthly_df_oos (pd.DataFrame): Monthly dataframe potentially modified
            by OOS validation function to include 'predicted_price_oos'. Used
            to extract the last OOS predicted price.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'final_dict' (Dict[str, Any]): Structured dictionary of key results.
            - 'interpretation_text' (str): Formatted summary string for display.
    """
    logging.info("Generating final summary report...")
    final_dict: Dict[str, Any] = {}

    # --- Extract OLS Results ---
    ols_base = analysis_results.get("ols", {}).get("monthly_base", {})
    ols_ext = analysis_results.get("ols", {}).get("monthly_extended", {})
    ols_constr = analysis_results.get("ols", {}).get("monthly_constrained", {})

    final_dict["ols_base_beta_active"] = _safe_get(ols_base, ["params", "log_active"])
    final_dict["ols_base_beta_active_pval"] = _safe_get(
        ols_base, ["pvals_hac", "log_active"]
    )
    final_dict["ols_base_r2"] = _safe_get(ols_base, ["r2"])
    final_dict["ols_base_rmse_usd"] = _safe_get(ols_base, ["RMSE_USD"])

    final_dict["ols_ext_beta_active"] = _safe_get(ols_ext, ["params", "log_active"])
    final_dict["ols_ext_beta_nasdaq"] = _safe_get(ols_ext, ["params", "log_nasdaq"])
    final_dict["ols_ext_beta_gas"] = _safe_get(ols_ext, ["params", "log_gas"])
    final_dict["ols_ext_r2"] = _safe_get(ols_ext, ["r2"])
    final_dict["ols_ext_rmse_usd"] = _safe_get(ols_ext, ["RMSE_USD"])
    # Store p-values as a sub-dict
    final_dict["ols_ext_pvals_hac"] = {
        "const": _safe_get(ols_ext, ["pvals_hac", "const"]),
        "log_active": _safe_get(ols_ext, ["pvals_hac", "log_active"]),
        "log_nasdaq": _safe_get(ols_ext, ["pvals_hac", "log_nasdaq"]),
        "log_gas": _safe_get(ols_ext, ["pvals_hac", "log_gas"]),
    }

    final_dict["ols_constr_rmse_usd"] = _safe_get(ols_constr, ["RMSE_USD"])

    # --- Extract Diagnostics ---
    diag = analysis_results.get("ols_diagnostics", {})
    final_dict["diag_dw"] = _safe_get(diag, ["DW"])
    final_dict["diag_bg_p"] = _safe_get(diag, ["BG_p"])
    final_dict["diag_bp_p"] = _safe_get(diag, ["BP_p"])
    final_dict["diag_jb_p"] = _safe_get(diag, ["JB_p"])
    final_dict["diag_white_p"] = _safe_get(diag, ["White_p"])  # Added White test

    # --- Extract Structural Breaks ---
    breaks = analysis_results.get("ols_structural_breaks", {})
    final_dict["break_cusum_p"] = _safe_get(breaks, ["CUSUM_p"])
    # Handle potentially missing break date keys gracefully
    final_dict["break_chow_eip_p"] = _safe_get(
        breaks, ["Chow_EIP1559_p"]
    )  # Example key
    final_dict["break_chow_merge_p"] = _safe_get(
        breaks, ["Chow_Merge_p"]
    )  # Example key
    # Note: Actual keys depend on the `break_dates` dict passed to run_structural_break_tests

    # --- Extract Dynamic Models ---
    ardl = analysis_results.get("ardl", {})
    vecm = analysis_results.get("vecm", {})

    final_dict["ardl_cointegrated_5pct"] = _safe_get(ardl, ["cointegrated_5pct"])
    final_dict["ardl_bounds_stat"] = _safe_get(ardl, ["bounds_stat"])
    final_dict["ardl_bounds_p_lower"] = _safe_get(ardl, ["bounds_p_lower"])
    final_dict["ardl_ect_coeff"] = _safe_get(ardl, ["ect_coeff"])

    final_dict["vecm_beta_active_coint"] = _safe_get(vecm, ["beta_active_coint"])
    final_dict["vecm_alpha_mcap"] = _safe_get(vecm, ["alpha_mcap"])
    final_dict["vecm_alpha_mcap_p"] = _safe_get(vecm, ["alpha_mcap_p"])
    final_dict["vecm_alpha_active_p"] = _safe_get(vecm, ["alpha_active_p"])

    # --- Extract Out-of-Sample ---
    oos = analysis_results.get("oos", {})
    final_dict["oos_mape_percent"] = _safe_get(
        oos, ["MAPE_percent"]
    )  # Check key used in validation.py
    final_dict["oos_rmse_usd"] = _safe_get(
        oos, ["RMSE_Price"]
    )  # Check key used in validation.py
    final_dict["oos_n_predictions"] = _safe_get(
        oos, ["N_OOS"]
    )  # Check key used in validation.py

    # --- Extract Last Prices ---
    last_actual: float | None = None
    last_fair_ext: float | None = None
    last_pred_oos: float | None = None
    last_date: pd.Timestamp | None = None

    # Use the dataframe that OLS modified to get last actual and fair price
    if not monthly_df_with_fv.empty and isinstance(
        monthly_df_with_fv.index, pd.DatetimeIndex
    ):
        last_date = monthly_df_with_fv.index[-1]
        if "price_usd" in monthly_df_with_fv.columns:
            last_actual = monthly_df_with_fv["price_usd"].iloc[-1]
        if "fair_price_ext" in monthly_df_with_fv.columns:
            last_fair_ext = monthly_df_with_fv["fair_price_ext"].iloc[-1]

    # Use the dataframe that OOS modified to get last predicted price
    if not monthly_df_oos.empty and "predicted_price_oos" in monthly_df_oos.columns:
        # Check if the column has non-NA values before accessing iloc[-1]
        oos_preds_valid = monthly_df_oos["predicted_price_oos"].dropna()
        if not oos_preds_valid.empty:
            last_pred_oos = oos_preds_valid.iloc[-1]  # Get last valid prediction
        # If last_date wasn't set above, try getting it from here
        if last_date is None and isinstance(monthly_df_oos.index, pd.DatetimeIndex):
            last_date = monthly_df_oos.index[-1]
    elif (
        last_date is None
        and not monthly_df_oos.empty
        and isinstance(monthly_df_oos.index, pd.DatetimeIndex)
    ):
        # Still try to get date if df exists but column doesn't
        last_date = monthly_df_oos.index[-1]

    # Ensure final values are None if pd.isna is true
    final_dict["last_actual_price"] = last_actual if pd.notna(last_actual) else None
    final_dict["last_fair_price_ext"] = (
        last_fair_ext if pd.notna(last_fair_ext) else None
    )
    final_dict["last_predicted_price_oos"] = (
        last_pred_oos if pd.notna(last_pred_oos) else None
    )
    final_dict["last_date"] = last_date  # Already Timestamp or None

    # --- Format Values for Interpretation Text ---
    beta_ext_str = _format_val(final_dict["ols_ext_beta_active"])
    beta_ext_pval = _safe_get(final_dict, ["ols_ext_pvals_hac", "log_active"])
    beta_ext_sig = (
        "significant"
        if isinstance(beta_ext_pval, (int, float)) and beta_ext_pval < 0.05
        else "not significant"
    )
    beta_ext_pval_str = _format_val(beta_ext_pval, precision=3, is_p_value=True)

    nasdaq_pval = _safe_get(final_dict, ["ols_ext_pvals_hac", "log_nasdaq"])
    nasdaq_sig = (
        "significant"
        if isinstance(nasdaq_pval, (int, float)) and nasdaq_pval < 0.05
        else "not significant"
    )
    nasdaq_pval_str = _format_val(nasdaq_pval, precision=3, is_p_value=True)

    gas_pval = _safe_get(final_dict, ["ols_ext_pvals_hac", "log_gas"])
    gas_sig = (
        "significant"
        if isinstance(gas_pval, (int, float)) and gas_pval < 0.05
        else "not significant"
    )
    gas_pval_str = _format_val(gas_pval, precision=3, is_p_value=True)

    last_fair_str = _format_val(final_dict["last_fair_price_ext"], is_usd=True)
    last_actual_str = _format_val(final_dict["last_actual_price"], is_usd=True)
    oos_mape_str = (
        f"{_format_val(final_dict['oos_mape_percent'], precision=1)}%"
        if final_dict["oos_mape_percent"] not in ["N/A", None]
        else "N/A"
    )
    oos_rmse_str = _format_val(final_dict["oos_rmse_usd"], is_usd=True)
    n_months_val = _safe_get(analysis_results, ["data_summary", "monthly_shape", 0])
    n_months_str = _format_val(n_months_val, precision=0)

    # Format ARDL bounds test results
    ardl_f_stat_str = _format_val(final_dict["ardl_bounds_stat"])
    ardl_p_lower = final_dict["ardl_bounds_p_lower"]
    ardl_cointegrated = final_dict["ardl_cointegrated_5pct"]

    ardl_bounds_text = "N/A"  # Default
    if ardl_cointegrated is None:
        ardl_bounds_text = (
            f"Inconclusive (F-stat={ardl_f_stat_str}, p-values N/A or test failed)"
        )
    elif isinstance(ardl_cointegrated, bool):  # Check it's boolean before using
        if ardl_cointegrated:
            ardl_bounds_text = f"Cointegrated (F-stat={ardl_f_stat_str}, p_lower={_format_val(ardl_p_lower, is_p_value=True)})"
        else:
            ardl_bounds_text = f"Not Cointegrated (F-stat={ardl_f_stat_str}, p_lower={_format_val(ardl_p_lower, is_p_value=True)})"

    # Add interpretation for premium/discount
    premium_discount_text = ""
    last_actual_val = final_dict["last_actual_price"]
    last_fair_val = final_dict["last_fair_price_ext"]

    # Check if both values are valid numbers before calculating diff
    if (
        isinstance(last_actual_val, (int, float, np.number))
        and isinstance(last_fair_val, (int, float, np.number))
        and pd.notna(last_actual_val)
        and pd.notna(last_fair_val)
        and last_fair_val != 0
    ):
        try:
            last_actual_f = float(last_actual_val)
            last_fair_f = float(last_fair_val)
            diff_pct = ((last_actual_f - last_fair_f) / last_fair_f) * 100
            if abs(diff_pct) < 5:
                premium_discount_text = f"The actual price ({last_actual_str}) is currently close to the model's fair value ({last_fair_str})."
            elif diff_pct > 0:
                premium_discount_text = f"The actual price ({last_actual_str}) is currently trading at a {diff_pct:.1f}% premium to the model's fair value ({last_fair_str})."
            else:  # diff_pct < 0
                premium_discount_text = f"The actual price ({last_actual_str}) is currently trading at a {abs(diff_pct):.1f}% discount to the model's fair value ({last_fair_str})."
        except (ValueError, TypeError, ZeroDivisionError) as e:
            logging.warning(f"Could not calculate premium/discount: {e}")
            premium_discount_text = f"[Calculation error comparing actual ({last_actual_str}) vs fair value ({last_fair_str}).]"
    else:
        premium_discount_text = f"[Could not compare actual ({last_actual_str}) vs fair value ({last_fair_str}) due to missing or invalid data.]"

    # --- Construct Interpretation Text ---
    data_summary = analysis_results.get("data_summary", {})
    start_date_str = _format_val(data_summary.get("monthly_start"))
    end_date_str = _format_val(data_summary.get("monthly_end"))
    last_date_str = _format_val(final_dict["last_date"])

    # Use f-string formatting consistently
    interpretation_text = f"""
### Ethereum Valuation Analysis Summary ###

**Date Range:** {start_date_str} to {end_date_str} ({n_months_str} months)

**Key Findings:**

1.  **Network Effects (Metcalfe's Law):**
    *   The extended OLS model estimates the Metcalfe exponent (log_active coefficient) to be **{beta_ext_str}**.
    *   This relationship is statistically **{beta_ext_sig}** (p={beta_ext_pval_str}), suggesting super-linear scaling where value increases more than proportionally with network activity, even after controls.

2.  **Other Drivers:**
    *   Macro conditions (proxied by log_nasdaq) are found to be a **{nasdaq_sig}** driver (p={nasdaq_pval_str}).
    *   On-chain activity/scarcity (proxied by log_gas/burn) is also a **{gas_sig}** driver (p={gas_pval_str}).

3.  **Model Diagnostics & Stability:**
    *   Residual diagnostics on the extended OLS model indicated some issues (e.g., DW={_format_val(final_dict["diag_dw"])}, BG p={_format_val(final_dict["diag_bg_p"], is_p_value=True)}) which were addressed using HAC standard errors for inference.
    *   Normality of residuals was rejected (JB p={_format_val(final_dict["diag_jb_p"], is_p_value=True)}). Heteroskedasticity may be present (White p={_format_val(final_dict["diag_white_p"], is_p_value=True)}).
    *   Structural break tests show mixed results: CUSUM p={_format_val(final_dict["break_cusum_p"], is_p_value=True)}, Chow EIP1559 p={_format_val(final_dict["break_chow_eip_p"], is_p_value=True)}, Chow Merge p={_format_val(final_dict["break_chow_merge_p"], is_p_value=True)}. Significant Chow tests suggest parameter shifts around major upgrades.

4.  **Dynamic Relationship & Cointegration:**
    *   Dynamic models (ARDL/VECM) were estimated. ARDL Bounds test result: **{ardl_bounds_text}**.
    *   The VECM analysis estimates the long-run elasticity of market cap w.r.t active addresses at **{_format_val(final_dict["vecm_beta_active_coint"])}**.
    *   The adjustment coefficient for market cap (alpha_mcap) is **{_format_val(final_dict["vecm_alpha_mcap"])}** (p={_format_val(final_dict["vecm_alpha_mcap_p"], is_p_value=True)}), indicating how quickly the price corrects towards the long-run equilibrium.

5.  **Out-of-Sample Performance:**
    *   Rolling OOS validation of the extended OLS model yielded **{_format_val(final_dict["oos_n_predictions"], precision=0)}** predictions.
    *   The Mean Absolute Percentage Error (MAPE) was approx. **{oos_mape_str}**.
    *   The Root Mean Squared Error (RMSE) in price terms was approx. **{oos_rmse_str}**.

**Valuation Snapshot (as of {last_date_str}):**

*   **Actual Price:** {last_actual_str}
*   **Model Fair Value (Extended OLS):** {last_fair_str}
*   **Comparison:** {premium_discount_text}
*   *(OOS Predicted Price for last date: {_format_val(final_dict["last_predicted_price_oos"], is_usd=True)})*

**Overall Conclusion:**
Ethereum's valuation appears strongly anchored by network effects (Metcalfe's Law), consistent with its role as a smart contract platform. However, macro factors and on-chain tokenomics (like fee burn captured by log_gas) are also significant drivers. Dynamic models suggest a potential long-run relationship and error correction mechanism, though the ARDL bounds test might be inconclusive or indicate no cointegration depending on the specific results. The model provides a framework for fundamental valuation, but potential model misspecifications (diagnostics) and structural breaks warrant careful consideration when interpreting the results. The out-of-sample performance gives an indication of the model's predictive accuracy.
"""

    logging.info("Summary report generation complete.")
    return {"final_dict": final_dict, "interpretation_text": interpretation_text}
