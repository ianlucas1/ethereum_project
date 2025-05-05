# src/utils/api_helpers.py

"""
Utility helpers for robust HTTP API calls and snapshot saving using requests.Session.

All functions are typed for mypy --strict and are safe for
head-less CI (no disk-writes unless a directory is provided).

Dependencies:
    * requests 2.x
    * urllib3 1.x (comes with requests)
    * python-dotenv (optional) for `.env` loading
"""

from __future__ import annotations

import json
import logging

# Removed time import as retries are handled by the session adapter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Final, Mapping, MutableMapping, Optional

import requests

# Imports for Session and Retry logic
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException  # Import base RequestException
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------
# Constants & types
# ---------------------------------------------------------------------

_DEFAULT_HEADERS: Final[Mapping[str, str]] = {
    "User-Agent": "ethereum_project/1.0 (+https://github.com/ianlucas1/ethereum_project)"
}

Json = Dict[str, Any]

# ---------------------------------------------------------------------
# Session with Retry Configuration
# ---------------------------------------------------------------------

# Configure retry strategy
# Retries on 5xx errors, respects Retry-After header, exponential backoff
retry_strategy = Retry(
    total=3,  # Total number of retries to allow (initial + 2 retries)
    status_forcelist=[429, 500, 502, 503, 504],  # Status codes to retry on
    allowed_methods=["HEAD", "GET", "OPTIONS"],  # Retry only on idempotent methods
    backoff_factor=1,  # sleep for {backoff factor} * (2 ** ({number of total retries} - 1))
    # Note: urllib3 default includes handling of Retry-After header
)

# Create an adapter with the retry strategy
adapter = HTTPAdapter(max_retries=retry_strategy)

# Create a global session object
session = requests.Session()

# Mount the adapter to the session for both HTTP and HTTPS
session.mount("http://", adapter)
session.mount("https://", adapter)

# ---------------------------------------------------------------------
# Snapshot helper
# ---------------------------------------------------------------------


def _save_api_snapshot(
    directory: Path,
    filename_prefix: str,
    data: Any,
    *,
    suffix: str = ".json",
    indent: int = 2,
) -> Path:
    """
    Save `data` as JSON to `directory` using an ISO timestamped filename.

    Returns the Path written (for logging / tests).
    """
    directory.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_path = directory / f"{filename_prefix}_{ts}{suffix}"
    file_path.write_text(json.dumps(data, indent=indent, default=str))
    return file_path


# ---------------------------------------------------------------------
# Robust GET wrapper (using Session)
# ---------------------------------------------------------------------


def robust_get(
    url: str,
    params: Optional[Mapping[str, Any]] = None,
    *,
    headers: Optional[Mapping[str, str]] = None,
    # max_retries and backoff_sec are now handled by the session adapter
    timeout: float = 15.0,
    snapshot_dir: Optional[Path] = None,
    snapshot_prefix: str = "api_snapshot",  # Added prefix parameter
) -> Json:
    """
    GET `url` using the global session with built-in retry logic.

    Args
    ----
    url:
        Full endpoint URL.
    params:
        Query-string parameters.
    headers:
        Additional request headers (merged with session headers and `_DEFAULT_HEADERS`).
    timeout:
        Per-request timeout in seconds.
    snapshot_dir:
        If provided, the successful response body is written to
        that directory for offline debugging / golden snapshots.
    snapshot_prefix:
        Filename prefix for the snapshot file (defaults to "api_snapshot").

    Returns
    -------
    Parsed JSON (dict).

    Raises
    ------
    requests.exceptions.RequestException
        If the request fails after exhausting retries (includes HTTPError, Timeout, etc.).
    ValueError
        If the response body is not JSON or not a top-level object.
    """
    merged_headers: MutableMapping[str, str] = dict(_DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)

    try:
        # Use the global session object
        resp = session.get(
            url,
            params=None if params is None else dict(params),
            headers=merged_headers,
            timeout=timeout,
        )
        # raise_for_status() is called implicitly by the adapter/retry logic
        # for statuses in retry_strategy.status_forcelist.
        # We still need to check for other 4xx errors if not in the forcelist.
        resp.raise_for_status()  # Check for any non-retried 4xx/5xx errors

        # Attempt to parse JSON
        try:
            data: Any = resp.json()
        except json.JSONDecodeError as json_err:
            logging.error(f"Failed to decode JSON response from {url}: {json_err}")
            logging.debug(f"Response text: {resp.text[:500]}...")  # Log snippet of text
            raise ValueError(f"Response from {url} is not valid JSON.") from json_err

        # Save snapshot if requested
        if snapshot_dir:
            try:
                _save_api_snapshot(
                    snapshot_dir,
                    snapshot_prefix,
                    data,  # Use the provided prefix
                )
            except Exception as snap_err:
                # Log error but don't fail the request
                logging.error(
                    f"Failed to save API snapshot for {url}: {snap_err}", exc_info=True
                )

        # Ensure the result is a dictionary (top-level JSON object)
        if not isinstance(data, dict):
            logging.error(
                f"Expected top-level JSON object from {url}, got {type(data)}"
            )
            raise ValueError(
                f"Expected top-level JSON object from {url}, got {type(data)}"
            )

        return data

    except RequestException as exc:
        # This catches errors after retries are exhausted or non-retried errors
        logging.error(
            f"robust_get failed for {url} after retries (if applicable): {exc}"
        )
        raise  # Re-raise the final exception (e.g., HTTPError, ConnectionError, Timeout)
