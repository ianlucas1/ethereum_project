# src/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
# Useful for local development without setting system env vars
dotenv_path = Path('.') / '.env' # Assumes .env file is in the project root
load_dotenv(dotenv_path=dotenv_path)

# --- Project Root and Data Directory ---
# Assumes config.py is in src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# --- API Keys ---
# Load from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
CM_API_KEY = os.getenv("CM_API_KEY") # Optional

# --- Data Fetching Parameters ---
# Start dates could be configurable if needed
ETH_PRICE_START_DATE = "2017-11-09" # YYYY-MM-DD
CM_METRICS_START_DATE = "2015-08-01" # YYYY-MM-DD
NASDAQ_START_DATE = "1985-01-01" # YYYY-MM-DD

# Cache settings
CACHE_MAX_AGE_HOURS = 24

# --- EDA / Preprocessing Parameters ---
WINSORIZE_COLS = ["active_addr", "burn", "tx_count"]
WINSORIZE_QUANTILE = 0.995
STATIONARITY_COLS = ["log_marketcap", "log_active", "log_gas"]

# --- Modeling Parameters ---
# OLS
OLS_HAC_LAGS = 12
OLS_EXT_COLS = ["log_active", "log_nasdaq", "log_gas"]
OLS_CONSTR_BETA = 2.0

# Structural Breaks
BREAK_DATES = {
    "EIP1559": "2021-08-31",
    "Merge": "2022-09-30"
}

# VECM
VECM_ENDOG_COLS = ["log_marketcap", "log_active"]
VECM_EXOG_COLS = ["log_nasdaq", "log_gas"]
VECM_MAX_LAGS = 6
VECM_COINT_RANK = 1
VECM_DET_ORDER = 0 # 0: constant term in cointegration relation

# ARDL
ARDL_ENDOG_COL = "log_marketcap"
ARDL_EXOG_COLS = ["log_active", "log_nasdaq", "log_gas"]
ARDL_MAX_LAGS = 6 # Max lag for auto-selection (if used) or reference
ARDL_TREND = 'c' # Trend ('n', 'c', 't', 'ct')
# Fixed lags used in current implementation:
ARDL_FIXED_P = 2
ARDL_FIXED_Q_ORDER = {name: 1 for name in ARDL_EXOG_COLS}

# OOS Validation
OOS_WINDOW = 24
OOS_ENDOG_COL = "log_marketcap"
OOS_EXOG_COLS = ["log_active", "log_nasdaq", "log_gas"]

# --- Output Configuration ---
RESULTS_JSON_FILENAME = "final_results.json"
RAW_PLOT_FILENAME = "raw_core_data_plot.png"

# --- Logging Configuration (Optional - can be kept in utils.py) ---
# LOG_LEVEL = "INFO"
# LOG_FORMAT = "%(asctime)s | %(levelname)s: %(message)s"
# LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Add basic validation for required keys ---
if not RAPIDAPI_KEY:
    # Log this issue - requires logging setup or print
    print("WARNING: RAPIDAPI_KEY environment variable not set in config.py. Data fetching may fail.")
    # Optionally raise an error if it's absolutely critical:
    # raise ValueError("RAPIDAPI_KEY environment variable is required but not set.") 