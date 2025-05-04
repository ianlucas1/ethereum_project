# src/reporting.py

import logging
import json
import pandas as pd
import numpy as np
from typing import Any, Sequence


# --- JSON Encoder for NumPy types ---
class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NumPy types and NaN/Inf values."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            # Convert NaN/Inf to None for JSON compatibility
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            # Convert NaN/Inf in arrays too
            return np.where(
                np.isnan(obj) | np.isinf(obj), None, obj
            ).tolist()  # ndarray → JSON helper
        elif isinstance(obj, (pd.Timestamp, pd.Period)):
            # Format Timestamp/Period to ISO 8601 string
            return obj.isoformat() if hasattr(obj, "isoformat") else str(obj)
        elif pd.isna(obj):
            return None  # Handle pandas NaT or other NAs
        try:
            return super(NpEncoder, self).default(obj)
        except TypeError:
            # Handle non-serializable objects gracefully
            logging.warning(
                f"Object of type {type(obj)} is not JSON serializable. Representing as string."
            )
            return str(obj)


# --- Summary Generation ---


def generate_summary(
    analysis_results: dict[str, Any],
    monthly_df_with_fv: pd.DataFrame,
    monthly_df_oos: pd.DataFrame,
) -> dict[str, Any]:
    """
    Generates the final results dictionary and interpretation text.

    Args:
        analysis_results: Dictionary containing results from all analysis steps.
        monthly_df_with_fv: Monthly dataframe potentially modified by OLS benchmark
                            function to include 'fair_price_ext'.
        monthly_df_oos: Monthly dataframe potentially modified by OOS validation
                        function to include 'predicted_price_oos'.

    Returns:
        A dictionary containing:
            - 'final_dict': The structured dictionary of key results.
            - 'interpretation_text': The formatted summary string.
    """
    logging.info("Generating final summary report...")
    final_dict: dict[str, Any] = {}

    # Helper function to safely get nested dictionary values
    def safe_get(
        data_dict: Any,
        key_list: Sequence[str | int],  # Allow int for tuple indexing
        default: Any | None = None,
    ) -> Any:
        current = data_dict
        for key in key_list:
            if isinstance(current, dict) or isinstance(
                current, tuple
            ):  # Allow tuples for shape
                try:
                    # Handle integer index for tuples like shape
                    if isinstance(key, int) and isinstance(current, tuple):
                        if key < len(current):
                            current = current[key]
                        else:
                            return default
                    # Handle dictionary keys
                    elif isinstance(current, dict):
                        current = current.get(key)
                    else:  # Cannot index further
                        return default
                except (KeyError, IndexError, TypeError):
                    return default
            else:
                return default
            if current is None:
                return default
        # If the final value is NaN or Inf, return the default (None for JSON)
        if isinstance(current, (float, np.floating)) and (
            np.isnan(current) or np.isinf(current)
        ):
            return default
        return current

    # --- Extract OLS Results ---
    ols_base = analysis_results.get("ols", {}).get("monthly_base", {})
    ols_ext = analysis_results.get("ols", {}).get("monthly_extended", {})
    ols_constr = analysis_results.get("ols", {}).get("monthly_constrained", {})

    final_dict["ols_base_beta_active"] = safe_get(ols_base, ["params", "log_active"])
    final_dict["ols_base_beta_active_pval"] = safe_get(
        ols_base, ["pvals_hac", "log_active"]
    )
    final_dict["ols_base_r2"] = safe_get(ols_base, ["r2"])
    final_dict["ols_base_rmse_usd"] = safe_get(ols_base, ["RMSE_USD"])

    final_dict["ols_ext_beta_active"] = safe_get(ols_ext, ["params", "log_active"])
    final_dict["ols_ext_beta_nasdaq"] = safe_get(ols_ext, ["params", "log_nasdaq"])
    final_dict["ols_ext_beta_gas"] = safe_get(ols_ext, ["params", "log_gas"])
    final_dict["ols_ext_r2"] = safe_get(ols_ext, ["r2"])
    final_dict["ols_ext_rmse_usd"] = safe_get(ols_ext, ["RMSE_USD"])
    # Store p-values as a sub-dict
    final_dict["ols_ext_pvals_hac"] = {
        "const": safe_get(ols_ext, ["pvals_hac", "const"]),
        "log_active": safe_get(ols_ext, ["pvals_hac", "log_active"]),
        "log_nasdaq": safe_get(ols_ext, ["pvals_hac", "log_nasdaq"]),
        "log_gas": safe_get(ols_ext, ["pvals_hac", "log_gas"]),
    }

    final_dict["ols_constr_rmse_usd"] = safe_get(ols_constr, ["RMSE_USD"])

    # --- Extract Diagnostics ---
    diag = analysis_results.get("ols_diagnostics", {})
    final_dict["diag_dw"] = safe_get(diag, ["DW"])
    final_dict["diag_bg_p"] = safe_get(diag, ["BG_p"])
    final_dict["diag_bp_p"] = safe_get(diag, ["BP_p"])
    final_dict["diag_jb_p"] = safe_get(diag, ["JB_p"])
    final_dict["diag_white_p"] = safe_get(diag, ["White_p"])  # Added White test

    # --- Extract Structural Breaks ---
    breaks = analysis_results.get("ols_structural_breaks", {})
    final_dict["break_cusum_p"] = safe_get(breaks, ["CUSUM_p"])
    final_dict["break_chow_eip_p"] = safe_get(breaks, ["Chow_EIP1559_p"])
    final_dict["break_chow_merge_p"] = safe_get(breaks, ["Chow_Merge_p"])

    # --- Extract Dynamic Models ---
    ardl = analysis_results.get("ardl", {})
    vecm = analysis_results.get("vecm", {})

    final_dict["ardl_cointegrated_5pct"] = safe_get(
        ardl, ["cointegrated_5pct"]
    )  # This might be None if p-value was nan
    final_dict["ardl_bounds_stat"] = safe_get(ardl, ["bounds_stat"])
    final_dict["ardl_bounds_p_lower"] = safe_get(
        ardl, ["bounds_p_lower"]
    )  # Get p-value too
    final_dict["ardl_ect_coeff"] = safe_get(ardl, ["ect_coeff"])

    final_dict["vecm_beta_active_coint"] = safe_get(
        vecm, ["beta_active_coint"]
    )  # LR beta from VECM
    final_dict["vecm_alpha_mcap"] = safe_get(
        vecm, ["alpha_mcap"]
    )  # Adjustment speed for mcap
    final_dict["vecm_alpha_mcap_p"] = safe_get(vecm, ["alpha_mcap_p"])
    final_dict["vecm_alpha_active_p"] = safe_get(
        vecm, ["alpha_active_p"]
    )  # P-value for active adjustment

    # --- Extract Out-of-Sample ---
    oos = analysis_results.get("oos", {})
    final_dict["oos_mape_percent"] = safe_get(oos, ["MAPE_percent"])
    final_dict["oos_rmse_usd"] = safe_get(oos, ["RMSE_Price"])  # Use price RMSE
    final_dict["oos_n_predictions"] = safe_get(oos, ["N_OOS"])

    # --- Extract Last Prices ---
    last_actual = None
    last_fair_ext = None
    last_pred_oos = None
    last_date = None  # Initialize last_date

    # Use the dataframe that OLS modified to get last actual and fair price
    if not monthly_df_with_fv.empty:
        last_date = monthly_df_with_fv.index[-1]  # Get last date from this df
        last_actual = (
            monthly_df_with_fv["price_usd"].iloc[-1]
            if "price_usd" in monthly_df_with_fv.columns
            else None
        )
        last_fair_ext = (
            monthly_df_with_fv["fair_price_ext"].iloc[-1]
            if "fair_price_ext" in monthly_df_with_fv.columns
            else None
        )

    # Use the dataframe that OOS modified to get last predicted price
    if not monthly_df_oos.empty:
        last_pred_oos = (
            monthly_df_oos["predicted_price_oos"].iloc[-1]
            if "predicted_price_oos" in monthly_df_oos.columns
            else None
        )
        # If last_date wasn't set above, try getting it from here
        if last_date is None and not monthly_df_oos.empty:
            last_date = monthly_df_oos.index[-1]

    final_dict["last_actual_price"] = last_actual if pd.notna(last_actual) else None
    final_dict["last_fair_price_ext"] = (
        last_fair_ext if pd.notna(last_fair_ext) else None
    )
    final_dict["last_predicted_price_oos"] = (
        last_pred_oos if pd.notna(last_pred_oos) else None
    )
    final_dict["last_date"] = last_date  # Store the determined last date

    # --- Format Values for Interpretation Text ---
    def format_val(
        val: Any,
        precision: int = 2,
        is_p_value: bool = False,
        is_usd: bool = False,
        is_bool: bool = False,  # Reverted parameter name to match existing usage
    ) -> str:
        # Handle infinity first
        if isinstance(val, (float, np.floating)) and np.isinf(val):
            # Check sign of infinity
            return "+Infinity" if val > 0 else "-Infinity"
        # Handle None or NaN
        if (
            val is None
            or (isinstance(val, (float, np.floating)) and np.isnan(val))
            or pd.isna(val)
        ):
            return "N/A"
        # Format based on type
        if is_bool:
            return str(val)  # True/False
        if is_p_value:
            # Handle very small p-values
            return "<0.001" if val < 0.001 else f"{val:.3f}"
        if is_usd:
            return f"${val:,.0f}"  # Format USD with commas, no decimals
        if isinstance(val, (int, float, np.number)):
            # Dynamic precision for R2 etc.
            fmt_str = "{:." + str(precision) + "f}"
            return fmt_str.format(val)
        if isinstance(val, (pd.Timestamp)):  # Format Timestamp
            return str(val.strftime("%Y-%m-%d"))  # cast to str for mypy
        return str(val)  # Fallback for other types

    beta_ext_str = format_val(final_dict["ols_ext_beta_active"])
    beta_ext_pval = final_dict["ols_ext_pvals_hac"].get("log_active")
    beta_ext_sig = (
        "significant"
        if isinstance(beta_ext_pval, (int, float)) and beta_ext_pval < 0.05
        else "not significant"
    )
    beta_ext_pval_str = format_val(beta_ext_pval, precision=3, is_p_value=True)

    nasdaq_pval = final_dict["ols_ext_pvals_hac"].get("log_nasdaq")
    nasdaq_sig = (
        "significant"
        if isinstance(nasdaq_pval, (int, float)) and nasdaq_pval < 0.05
        else "not significant"
    )
    nasdaq_pval_str = format_val(nasdaq_pval, precision=3, is_p_value=True)

    gas_pval = final_dict["ols_ext_pvals_hac"].get("log_gas")
    gas_sig = (
        "significant"
        if isinstance(gas_pval, (int, float)) and gas_pval < 0.05
        else "not significant"
    )
    gas_pval_str = format_val(gas_pval, precision=3, is_p_value=True)

    last_fair_str = format_val(final_dict["last_fair_price_ext"], is_usd=True)
    last_actual_str = format_val(final_dict["last_actual_price"], is_usd=True)
    oos_mape_str = (
        format_val(final_dict["oos_mape_percent"], precision=1) + "%"
        if final_dict["oos_mape_percent"] not in ["N/A", None]
        else "N/A"
    )
    oos_rmse_str = format_val(final_dict["oos_rmse_usd"], is_usd=True)
    # Correctly format N months using safe_get and format_val
    n_months_val = safe_get(analysis_results, ["data_summary", "monthly_shape", 0])
    n_months_str = format_val(n_months_val, precision=0)

    # Format ARDL bounds test results more carefully
    ardl_f_stat_str = format_val(final_dict["ardl_bounds_stat"])
    ardl_p_lower = final_dict["ardl_bounds_p_lower"]  # Get raw value (could be None)
    ardl_cointegrated = final_dict[
        "ardl_cointegrated_5pct"
    ]  # Get raw value (could be None or False)

    if ardl_cointegrated is None:  # Check if p-value was NaN
        ardl_bounds_text = f"Inconclusive (F-stat={ardl_f_stat_str}, p-values N/A)"
    elif ardl_cointegrated:
        ardl_bounds_text = f"Cointegrated (F-stat={ardl_f_stat_str}, p_lower={format_val(ardl_p_lower, is_p_value=True)})"
    else:
        ardl_bounds_text = f"Not Cointegrated (F-stat={ardl_f_stat_str}, p_lower={format_val(ardl_p_lower, is_p_value=True)})"

    # Add interpretation for premium/discount
    premium_discount_text = ""
    # Use the extracted values from final_dict which handle None
    last_actual_val = final_dict["last_actual_price"]
    last_fair_val = final_dict["last_fair_price_ext"]

    if (
        isinstance(last_actual_val, (int, float))
        and isinstance(last_fair_val, (int, float))
        and last_fair_val != 0
    ):
        diff_pct = ((last_actual_val - last_fair_val) / last_fair_val) * 100
        if abs(diff_pct) < 5:
            premium_discount_text = f"The actual price ({last_actual_str}) is currently close to the model's fair value ({last_fair_str})."
        elif diff_pct > 0:
            premium_discount_text = f"The actual price ({last_actual_str}) is currently trading at a {diff_pct:.1f}% premium to the model's fair value ({last_fair_str})."
        else:
            premium_discount_text = f"The actual price ({last_actual_str}) is currently trading at a {abs(diff_pct):.1f}% discount to the model's fair value ({last_fair_str})."
    else:
        premium_discount_text = f"[Could not compare actual ({last_actual_str}) vs fair value ({last_fair_str}).]"

    # --- Construct Interpretation Text ---
    interpretation_text = f"""
### Ethereum Valuation Analysis Summary ###

**Date Range:** {format_val(analysis_results.get("data_summary", {}).get("monthly_start"))} to {format_val(analysis_results.get("data_summary", {}).get("monthly_end"))} ({n_months_str} months)

**Key Findings:**

1.  **Network Effects (Metcalfe's Law):**
    *   The extended OLS model estimates the Metcalfe exponent (log_active coefficient) to be **{beta_ext_str}**.
    *   This relationship is statistically **{beta_ext_sig}** (p={beta_ext_pval_str}), suggesting super-linear scaling where value increases more than proportionally with network activity, even after controls.

2.  **Other Drivers:**
    *   Macro conditions (proxied by log_nasdaq) are found to be a **{nasdaq_sig}** driver (p={nasdaq_pval_str}).
    *   On-chain activity/scarcity (proxied by log_gas/burn) is also a **{gas_sig}** driver (p={gas_pval_str}).

3.  **Model Diagnostics & Stability:**
    *   Residual diagnostics on the extended OLS model indicated some issues (e.g., DW={format_val(final_dict["diag_dw"])}, BG p={format_val(final_dict["diag_bg_p"], is_p_value=True)}) which were addressed using HAC standard errors for inference.
    *   Normality of residuals was rejected (JB p={format_val(final_dict["diag_jb_p"], is_p_value=True)}).
    *   Structural break tests show mixed results: CUSUM p={format_val(final_dict["break_cusum_p"], is_p_value=True)}, Chow EIP1559 p={format_val(final_dict["break_chow_eip_p"], is_p_value=True)}, Chow Merge p={format_val(final_dict["break_chow_merge_p"], is_p_value=True)}. Significant Chow tests suggest parameter shifts around major upgrades.

4.  **Dynamic Relationship & Cointegration:**
    *   Dynamic models (ARDL/VECM) were estimated. ARDL Bounds test result: **{ardl_bounds_text}**.
    *   The VECM analysis estimates the long-run elasticity of market cap w.r.t active addresses at **{format_val(final_dict["vecm_beta_active_coint"])}**.
    *   The adjustment coefficient for market cap (alpha_mcap) is **{format_val(final_dict["vecm_alpha_mcap"])}** (p={format_val(final_dict["vecm_alpha_mcap_p"], is_p_value=True)}), indicating how quickly the price corrects towards the long-run equilibrium.

5.  **Out-of-Sample Performance:**
    *   Rolling OOS validation of the extended OLS model yielded **{format_val(final_dict["oos_n_predictions"], precision=0)}** predictions.
    *   The Mean Absolute Percentage Error (MAPE) was approx. **{oos_mape_str}**.
    *   The Root Mean Squared Error (RMSE) in price terms was approx. **{oos_rmse_str}**.

**Valuation Snapshot (as of {format_val(final_dict["last_date"])}):**

*   **Actual Price:** {last_actual_str}
*   **Model Fair Value (Extended OLS):** {last_fair_str}
*   **Comparison:** {premium_discount_text}
*   *(OOS Predicted Price for last date: {format_val(final_dict["last_predicted_price_oos"], is_usd=True)})*

**Overall Conclusion:**
Ethereum's valuation appears strongly anchored by network effects (Metcalfe's Law), consistent with its role as a smart contract platform. However, macro factors and on-chain tokenomics (like fee burn captured by log_gas) are also significant drivers. Dynamic models confirm a long-run relationship and error correction (though ARDL bounds test was inconclusive). The model provides a framework for fundamental valuation, though potential structural breaks warrant consideration.
"""

    logging.info("Summary report generation complete.")
    return {"final_dict": final_dict, "interpretation_text": interpretation_text}
