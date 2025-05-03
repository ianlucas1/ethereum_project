# src/utils.py

import os
import time
import logging
import json
import random
import shutil
from datetime import datetime, timedelta, timezone
from typing import Callable, Any # Or just Callable if Any isn't used directly here
import requests
import pandas as pd
import numpy as np # Added numpy as it might be needed indirectly or later
from pathlib import Path

# Import settings from config
from src.config import settings

# Safe import for filelock - raise error if missing
try:
    from filelock import FileLock
except ModuleNotFoundError as e:
    raise ImportError(
        "'filelock' is missing. Activate your venv and run "
        "'pip install -r requirements-lock.txt'"
    ) from e


# --- Logging Setup ---
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


# --- Constants ---
# DATA_DIR is now sourced from settings
# Ensure data dir exists when this module is imported
# Use try-except for robustness if permissions are an issue
try:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logging.error(f"Could not create data directory {settings.DATA_DIR}: {e}")
    # Depending on the use case, you might want to exit or just warn
    # sys.exit(f"Failed to create data directory: {e}")


# --- Helper Functions ---

def disk_cache(path_arg: str, max_age_hr: int = 24) -> Callable:
    """Decorator to cache pandas DataFrame/Series to disk (Parquet)."""
    # Use DATA_DIR from settings
    cache_path = settings.DATA_DIR / path_arg
    lock_path  = cache_path.with_suffix(".lock")

    # Determine if the decorated function returns Series or DataFrame for saving
    # This is a bit tricky without inspecting the function signature more deeply
    # We'll assume DataFrame by default for saving, Series can be saved via to_frame()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs) -> Any:
            # Check cache existence and age
            if cache_path.exists():
                try:
                    cache_mtime_ts = cache_path.stat().st_mtime
                    cache_mtime = datetime.fromtimestamp(cache_mtime_ts, tz=timezone.utc)
                    now = datetime.now(tz=timezone.utc)
                    age = now - cache_mtime
                    if age < timedelta(hours=max_age_hr):
                        logging.info("Using cached %s (%.1fhr old)",
                                     cache_path.name, age.total_seconds() / 3600)
                        # Load data
                        loaded_data = pd.read_parquet(cache_path)
                        # Ensure loaded data has timezone-naive index AFTER loading
                        if pd.api.types.is_datetime64_any_dtype(loaded_data.index) and loaded_data.index.tz is not None:
                            loaded_data.index = loaded_data.index.tz_localize(None)

                        # If original function returned Series, try returning the first column
                        # This is heuristic - might need adjustment based on actual usage
                        if isinstance(loaded_data, pd.DataFrame) and len(loaded_data.columns) == 1:
                             # Check if the original function likely returned a Series
                             # This check isn't perfect. A better way might be needed if issues arise.
                             # For now, assume if saved df has 1 col, Series was intended.
                             return loaded_data.iloc[:, 0]
                        return loaded_data # Return DataFrame
                except Exception as e:
                    logging.warning(f"Failed to load or check cache {cache_path}: {e}. Re-fetching.")

            # Execute function, acquire lock, save result
            with FileLock(lock_path):
                logging.info(f"Cache miss or expired for {cache_path.name}. Calling function {func.__name__}.")
                result = func(*args, **kwargs)
                tmp_path = cache_path.with_suffix(".tmp")

                # Ensure data index is timezone-naive BEFORE saving
                if hasattr(result, 'index') and pd.api.types.is_datetime64_any_dtype(result.index) and result.index.tz is not None:
                    result.index = result.index.tz_localize(None)

                try:
                    # Save result to temporary file
                    if isinstance(result, pd.Series):
                        result.to_frame().to_parquet(tmp_path, index=True) # Save Series as one-column DataFrame
                    elif isinstance(result, pd.DataFrame):
                        result.to_parquet(tmp_path, index=True)
                    else:
                        logging.error(f"Cannot cache result of type {type(result)} from {func.__name__}.")
                        return result # Return uncached result if not DataFrame/Series

                    # Move temporary file to final cache path
                    shutil.move(tmp_path, cache_path)
                    logging.info(f"Saved fresh data to cache: {cache_path.name}")

                except Exception as e:
                    logging.error(f"Failed to save cache file {cache_path}: {e}")
                    # Clean up temp file if it exists
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except OSError as unlink_e:
                            logging.error(f"Failed to remove temporary cache file {tmp_path}: {unlink_e}")
            return result
        return wrapper
    return decorator


def _save_api_snapshot(directory: Path, filename_prefix: str, data: Any):
    """Saves the given data as a timestamped JSON snapshot."""
    try:
        # Ensure the snapshot directory exists
        directory.mkdir(parents=True, exist_ok=True)
        # Create timestamped filename
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filepath = directory / f"{filename_prefix}_{ts}.json"
        # Write data to JSON file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        logging.debug(f"Saved API snapshot to: {filepath.name}")
    except Exception as e:
        # Log error but don't interrupt the main flow
        logging.error(f"Failed to save API snapshot {filename_prefix}: {e}", exc_info=False)


def robust_get(url: str, headers=None, params=None, snapshot_prefix: str | None = None, retries=4, base_delay=4):
    """Robustly performs a GET request with retries and exponential backoff."""
    for n in range(retries):
        response = None # Initialize response
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            # Check for empty or non-JSON response before decoding
            if not response.content:
                 logging.warning(f"Empty response received from {url}. Status: {response.status_code}.")
                 # Decide how to handle empty: retry or return None/raise? Let's retry.
                 raise requests.exceptions.RequestException("Empty response content")

            # Decode JSON once here
            json_data = response.json()

            # Save snapshot if requested
            if snapshot_prefix:
                # Assuming settings.RAW_SNAPSHOT_DIR is accessible
                _save_api_snapshot(settings.RAW_SNAPSHOT_DIR, snapshot_prefix, json_data)

            return json_data # Return the decoded data
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else "N/A"
            logging.warning("Request failed: %s (Status: %s) — retrying in %.1fs (%d/%d)",
                            e, status_code, base_delay * 2**n + random.uniform(0, 1), n+1, retries)
            time.sleep(base_delay * 2**n + random.uniform(0, 1))
        except json.JSONDecodeError as e_json:
             # Use response captured at the start of the try block
             status = response.status_code if response is not None else "N/A"
             text_snippet = response.text[:200] if response is not None else "N/A"
             logging.error("Failed to decode JSON response from %s. Status: %s, Response text: %s... — retrying in %.1fs (%d/%d)",
                           url, status, text_snippet, base_delay * 2**n + random.uniform(0, 1), n+1, retries,
                           exc_info=True) # Add exc_info for detailed traceback
             time.sleep(base_delay * 2**n + random.uniform(0, 1))
        except Exception as e_other: # Catch any other unexpected errors during request/parsing
            logging.error("Unexpected error during GET request to %s: %s — retrying in %.1fs (%d/%d)",
                           url, e_other, base_delay * 2**n + random.uniform(0, 1), n+1, retries,
                           exc_info=True)
            time.sleep(base_delay * 2**n + random.uniform(0, 1))


    logging.error(f"GET {url} failed after {retries} retries")
    raise RuntimeError(f"GET {url} failed after {retries} retries")


def load_parquet(path: Path, req_cols: list[str] | None = None) -> pd.DataFrame:
    """Loads parquet, ensures 'time' index, checks columns."""
    if not path.exists():
        logging.error(f"Parquet file not found: {path}")
        raise FileNotFoundError(path)
    try:
        df = pd.read_parquet(path)
        # Ensure 'time' column exists before setting index
        if "time" not in df.columns:
            if df.index.name == "time":
                 df = df.reset_index() # Reset if 'time' is already the index name
            else:
                 # Fallback: If index has no name or different name, reset and rename first col
                 logging.warning(f"Parquet {path.name} missing 'time' column, using index or first column.")
                 # Try using index if it's datetime-like, otherwise use first column
                 if pd.api.types.is_datetime64_any_dtype(df.index):
                     col_name = df.index.name or "index_col" # Use index name or default
                     df = df.reset_index().rename(columns={col_name: "time"})
                 elif len(df.columns) > 0:
                     # If index isn't datetime, try resetting and using the first column if it exists
                     original_cols = df.columns.tolist()
                     df = df.reset_index(drop=True) # Drop the non-datetime index
                     # Check if first column looks like time after reset
                     if pd.api.types.is_datetime64_any_dtype(df.iloc[:, 0]):
                         df = df.rename(columns={df.columns[0]: "time"})
                     else:
                         # If first column isn't time either, raise error
                         raise ValueError(f"Parquet {path.name} missing 'time' column and index/first column not suitable.")
                 else:
                     raise ValueError(f"Parquet {path.name} missing 'time' column and has no other columns.")


        # Convert to datetime, set index, sort, ensure timezone-naive
        df = (df.assign(time=lambda d: pd.to_datetime(d["time"]))
                .set_index("time")
                .sort_index())
        if df.index.tz is not None:
             df.index = df.index.tz_localize(None)

        if req_cols:
            missing_cols = [c for c in req_cols if c not in df.columns]
            if missing_cols:
                raise ValueError(f"{path.name} missing required columns: {missing_cols}")
        return df
    except Exception as e:
        logging.error(f"Failed to load or process parquet file {path}: {e}", exc_info=True)
        raise # Re-raise the exception after logging