# src/utils/api_helpers.py

import time
import logging
import json
import random
from datetime import datetime, timezone
from typing import Any
import requests
from pathlib import Path

# Import settings relative to the src directory
from src.config import settings


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
                # --- MODIFIED: Call package helper --- #
                from src import utils

                # Call the package-level helper, passing the correct arguments
                utils._save_api_snapshot(
                    settings.RAW_SNAPSHOT_DIR, snapshot_prefix, json_data
                )
                # --- END MODIFICATION --- #

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
