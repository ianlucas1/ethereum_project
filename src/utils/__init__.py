# src/utils/__init__.py - Consolidated utility functions

import time
import logging
import json
import random
from datetime import datetime, timezone
from typing import Any
import requests
import pandas as pd
from pathlib import Path
from src.config import settings

from .cache import disk_cache

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


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

# Note: disk_cache is imported above from .cache


def _save_api_snapshot(directory: Path, filename_prefix: str, data: Any):
    """Saves the given data as a timestamped JSON snapshot."""
    try:
        # Ensure the snapshot directory exists
        directory.mkdir(parents=True, exist_ok=True)
        # Create timestamped filename
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filepath = directory / f"{filename_prefix}_{ts}.json"
        # Write data to JSON file
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        logging.debug(f"Saved API snapshot to: {filepath.name}")
    except Exception as e:
        # Log error but don't interrupt the main flow
        logging.error(
            f"Failed to save API snapshot {filename_prefix}: {e}", exc_info=False
        )


def robust_get(
    url: str,
    headers=None,
    params=None,
    snapshot_prefix: str | None = None,
    retries=4,
    base_delay=4,
):
    """Robustly performs a GET request with retries and exponential backoff."""
    for n in range(retries):
        response = None  # Initialize response
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            # Check for empty or non-JSON response before decoding
            if not response.content:
                logging.warning(
                    f"Empty response received from {url}. Status: {response.status_code}."
                )
                # Decide how to handle empty: retry or return None/raise? Let's retry.
                raise requests.exceptions.RequestException("Empty response content")

            # Decode JSON once here
            json_data = response.json()

            # Save snapshot if requested
            if snapshot_prefix:
                # Assuming settings.RAW_SNAPSHOT_DIR is accessible
                _save_api_snapshot(
                    settings.RAW_SNAPSHOT_DIR, snapshot_prefix, json_data
                )

            return json_data  # Return the decoded data
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else "N/A"
            logging.warning(
                "Request failed: %s (Status: %s) — retrying in %.1fs (%d/%d)",
                e,
                status_code,
                base_delay * 2**n + random.uniform(0, 1),
                n + 1,
                retries,
            )
            time.sleep(base_delay * 2**n + random.uniform(0, 1))
        except json.JSONDecodeError:
            # Use response captured at the start of the try block
            status = response.status_code if response is not None else "N/A"
            text_snippet = response.text[:200] if response is not None else "N/A"
            logging.error(
                "Failed to decode JSON response from %s. Status: %s, Response text: %s... — retrying in %.1fs (%d/%d)",
                url,
                status,
                text_snippet,
                base_delay * 2**n + random.uniform(0, 1),
                n + 1,
                retries,
                exc_info=True,
            )  # Add exc_info for detailed traceback
            time.sleep(base_delay * 2**n + random.uniform(0, 1))
        except (
            Exception
        ) as e_other:  # Catch any other unexpected errors during request/parsing
            logging.error(
                "Unexpected error during GET request to %s: %s — retrying in %.1fs (%d/%d)",
                url,
                e_other,
                base_delay * 2**n + random.uniform(0, 1),
                n + 1,
                retries,
                exc_info=True,
            )
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
                df = df.reset_index()  # Reset if 'time' is already the index name
            else:
                # Fallback: If index has no name or different name, reset and rename first col
                logging.warning(
                    f"Parquet {path.name} missing 'time' column, using index or first column."
                )
                # Try using index if it's datetime-like, otherwise use first column
                if pd.api.types.is_datetime64_any_dtype(df.index):
                    col_name = df.index.name or "index_col"  # Use index name or default
                    df = df.reset_index().rename(columns={col_name: "time"})
                elif len(df.columns) > 0:
                    # If index isn't datetime, try resetting and using the first column if it exists
                    df.columns.tolist()
                    df = df.reset_index(drop=True)  # Drop the non-datetime index
                    # Check if first column looks like time after reset
                    if pd.api.types.is_datetime64_any_dtype(df.iloc[:, 0]):
                        df = df.rename(columns={df.columns[0]: "time"})
                    else:
                        # If first column isn't time either, raise error
                        raise ValueError(
                            f"Parquet {path.name} missing 'time' column and index/first column not suitable."
                        )
                else:
                    raise ValueError(
                        f"Parquet {path.name} missing 'time' column and has no other columns."
                    )

        # Convert to datetime, set index, sort, ensure timezone-naive
        df = (
            df.assign(time=lambda d: pd.to_datetime(d["time"]))
            .set_index("time")
            .sort_index()
        )
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        if req_cols:
            missing_cols = [c for c in req_cols if c not in df.columns]
            if missing_cols:
                raise ValueError(
                    f"{path.name} missing required columns: {missing_cols}"
                )
        return df
    except Exception as e:
        logging.error(
            f"Failed to load or process parquet file {path}: {e}", exc_info=True
        )
        raise  # Re-raise the exception after logging


__all__ = ["disk_cache", "_save_api_snapshot", "robust_get", "load_parquet"]
