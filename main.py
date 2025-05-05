# main.py
import json
import logging
import sys
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- #
# Project imports                                                             #
# --------------------------------------------------------------------------- #
from src.config import settings  # configuration / secrets
from src.data_processing import ensure_raw_data_exists, process_all_data
from src.diagnostics import run_residual_diagnostics, run_structural_break_tests
from src.eda import run_stationarity_tests, winsorize_data
from src.ols_models import run_ols_benchmarks
from src.reporting import NpEncoder, generate_summary
from src.ts_models import run_ardl_analysis, run_vecm_analysis
from src.validation import run_oos_validation

# --------------------------------------------------------------------------- #
# Local constants (previously in config)                                      #
# --------------------------------------------------------------------------- #
WINSORIZE_COLS = ["active_addr", "tx_count"]
WINSORIZE_QUANTILE = 0.99
STATIONARITY_COLS = ["price_usd", "active_addr", "tx_count"]

OLS_EXT_COLS = ["active_addr", "tx_count", "nasdaq"]

BREAK_DATES = {
    "break_1": "2017-11-01",
    "break_2": "2020-05-01",
}

VECM_ENDOG_COLS = ["price_usd", "active_addr"]
VECM_EXOG_COLS = ["nasdaq"]

ARDL_ENDOG_COL = "price_usd"
ARDL_EXOG_COLS = ["active_addr", "tx_count", "nasdaq"]

OOS_WINDOW = 60  # 5 years of monthly data
OOS_ENDOG_COL = "price_usd"
OOS_EXOG_COLS = ["active_addr", "tx_count", "nasdaq"]

RESULTS_JSON_FILENAME = "final_results.json"
RAW_PLOT_FILENAME = "raw_core_data_plot.png"

# --------------------------------------------------------------------------- #
# Main pipeline                                                               #
# --------------------------------------------------------------------------- #


def main() -> None:
    """Run the full Ethereum valuation analysis pipeline."""
    logging.info("--- Starting Ethereum Valuation Analysis ---")

    # 0 ─ Ensure raw data is present (download if required)
    logging.info("--- Checking/Fetching Raw Data ---")
    if not ensure_raw_data_exists(plot_diagnostics=True, filename=RAW_PLOT_FILENAME):
        logging.error("Could not ensure raw data is available. Exiting.")
        sys.exit(1)

    analysis_results: dict[str, Any] = {}

    # 1 ─ Data processing
    logging.info("--- Running Data Processing ---")
    daily_clean, monthly_clean = process_all_data()
    if daily_clean.empty or monthly_clean.empty:
        logging.error("Data processing failed or returned empty dataframes. Exiting.")
        sys.exit(1)

    analysis_results["data_summary"] = {
        "daily_shape": daily_clean.shape,
        "monthly_shape": monthly_clean.shape,
        "monthly_start": monthly_clean.index.min(),
        "monthly_end": monthly_clean.index.max(),
    }

    monthly_clean_original = monthly_clean.copy()
    monthly_clean_for_ols = monthly_clean.copy()

    # 2 ─ Pre-model EDA: winsorise + stationarity tests
    logging.info("--- Winsorising & Stationarity Tests ---")
    monthly_winsorized = winsorize_data(
        df=monthly_clean_original,
        cols_to_cap=WINSORIZE_COLS,
        quantile=WINSORIZE_QUANTILE,
        window_mask=None,  # whole data set
    )
    monthly_winsorized.replace([np.inf, -np.inf], np.nan, inplace=True)

    analysis_results["stationarity"] = run_stationarity_tests(
        df=monthly_winsorized,
        cols_to_test=STATIONARITY_COLS,
        window_mask=None,
    )

    # 3 ─ Modelling & diagnostics
    logging.info("--- Running Models ---")
    model_df = monthly_winsorized.dropna(
        subset=[ARDL_ENDOG_COL] + ARDL_EXOG_COLS
    ).copy()
    if model_df.empty:
        logging.error("No data left after NaN drop. Exiting.")
        sys.exit(1)

    # 3a OLS
    ols_results = run_ols_benchmarks(daily_clean, monthly_clean_for_ols)
    analysis_results["ols"] = ols_results

    # Diagnostics on extended OLS, if available
    ols_ext_fit = ols_results.get("monthly_extended", {})
    if ols_ext_fit.get("model_obj"):
        analysis_results["ols_diagnostics"] = run_residual_diagnostics(ols_ext_fit)
        analysis_results["ols_structural_breaks"] = run_structural_break_tests(
            ols_ext_fit, BREAK_DATES
        )
    else:
        analysis_results["ols_diagnostics"] = {"error": "Extended OLS failed"}
        analysis_results["ols_structural_breaks"] = {"error": "Extended OLS failed"}

    # 3b VECM
    vecm_req = VECM_ENDOG_COLS + VECM_EXOG_COLS
    if all(c in model_df.columns for c in vecm_req):
        analysis_results["vecm"] = run_vecm_analysis(
            model_df, VECM_ENDOG_COLS, VECM_EXOG_COLS
        )
    else:
        missing = set(vecm_req) - set(model_df.columns)
        analysis_results["vecm"] = {"error": f"Missing columns: {missing}"}

    # 3c ARDL
    ardl_req = [ARDL_ENDOG_COL] + ARDL_EXOG_COLS
    if all(c in model_df.columns for c in ardl_req):
        analysis_results["ardl"] = run_ardl_analysis(
            model_df, ARDL_ENDOG_COL, ARDL_EXOG_COLS
        )
    else:
        missing = set(ardl_req) - set(model_df.columns)
        analysis_results["ardl"] = {"error": f"Missing columns: {missing}"}

    # 3d OOS validation
    oos_req = [OOS_ENDOG_COL] + OOS_EXOG_COLS + ["price_usd", "supply"]
    if all(c in monthly_winsorized.columns for c in oos_req):
        oos_results = run_oos_validation(
            df_monthly=monthly_winsorized,
            endog_col=OOS_ENDOG_COL,
            exog_cols=OOS_EXOG_COLS,
            winsorize_cols=WINSORIZE_COLS,
            winsorize_quantile=WINSORIZE_QUANTILE,
            stationarity_cols=STATIONARITY_COLS,
            window_size=OOS_WINDOW,
        )
        analysis_results["oos"] = oos_results
        if "predictions_df" in oos_results:
            preds_df = oos_results["predictions_df"]
            model_df["predicted_price_oos"] = preds_df["predicted_price_oos"].reindex(
                model_df.index
            )
    else:
        missing = set(oos_req) - set(monthly_winsorized.columns)
        analysis_results["oos"] = {"error": f"Missing columns: {missing}"}

    # 4 ─ Reporting
    logging.info("--- Generating Report ---")
    summary = generate_summary(analysis_results, monthly_clean_for_ols, model_df)
    final_results = summary["final_dict"]
    interpretation_text = summary["interpretation_text"]

    print("\n" + "=" * 80)
    print(interpretation_text)
    print("=" * 80 + "\n")

    results_path = settings.DATA_DIR.parent / RESULTS_JSON_FILENAME
    try:
        with open(results_path, "w") as fp:
            json.dump(final_results, fp, indent=4, cls=NpEncoder)
        logging.info("Final results saved to %s", results_path)
    except Exception as exc:  # pragma: no cover
        logging.error("Failed to save results JSON: %s", exc, exc_info=True)

    logging.info("--- Pipeline finished ---")


# --------------------------------------------------------------------------- #
# CLI entry-point                                                             #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if not settings.RAPIDAPI_KEY:
        logging.error("RAPIDAPI_KEY environment variable not set. Exiting.")
        sys.exit(1)

    main()
