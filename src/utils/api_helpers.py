"""
Utility helpers for robust HTTP API calls and snapshot saving.

All functions are typed for mypy --strict and are safe for
head-less CI (no disk-writes unless a directory is provided).

Dependencies:
    * requests 2.x
    * python-dotenv (optional) for `.env` loading
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Final, Mapping, MutableMapping, Optional

import requests  # mypy.ini handles potential missing stubs

# ---------------------------------------------------------------------
# Constants & types
# ---------------------------------------------------------------------

_DEFAULT_HEADERS: Final[Mapping[str, str]] = {
    "User-Agent": "ethereum_project/1.0 (+https://github.com/ianlucas1/ethereum_project)"
}

Json = Dict[str, Any]

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
# Robust GET wrapper
# ---------------------------------------------------------------------


def robust_get(
    url: str,
    params: Optional[Mapping[str, Any]] = None,
    *,
    headers: Optional[Mapping[str, str]] = None,
    max_retries: int = 3,
    backoff_sec: float = 1.0,
    timeout: float = 15.0,
    snapshot_dir: Optional[Path] = None,
) -> Json:
    """
    GET `url` with exponential-backoff retry.

    Args
    ----
    url:
        Full endpoint URL.
    params:
        Query-string parameters.
    headers:
        Additional request headers (merged with `_DEFAULT_HEADERS`).
    max_retries:
        Total attempts (initial + retries).
    backoff_sec:
        Initial backoff; doubles each retry.
    timeout:
        Per-request timeout in seconds.
    snapshot_dir:
        If provided, every successful response body is written to
        that directory for offline debugging / golden snapshots.

    Returns
    -------
    Parsed JSON (dict).

    Raises
    ------
    requests.HTTPError
        If the final attempt fails (status >= 400).
    requests.RequestException
        For any network error after exhausting retries.
    ValueError
        If the response body is not JSON.
    """
    merged_headers: MutableMapping[str, str] = dict(_DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)

    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(
                url,
                params=None if params is None else dict(params),
                headers=merged_headers,
                timeout=timeout,
            )
            if resp.status_code >= 400:
                resp.raise_for_status()

            data: Any = resp.json()
            if snapshot_dir:
                _save_api_snapshot(
                    snapshot_dir, "api_snapshot", data
                )  # Prefix is hardcoded
            if not isinstance(data, dict):
                raise ValueError("Expected top-level JSON object")

            return data

        except (requests.RequestException, ValueError) as exc:
            # Note: HTTPError is a subclass of RequestException
            if attempt >= max_retries:
                logging.error("robust_get failed after %s attempts: %s", attempt, exc)
                raise  # Re-raise the caught exception (e.g., HTTPError, Timeout, ValueError)
            sleep_for = backoff_sec * 2 ** (attempt - 1)
            logging.warning(
                "Request failed (%s). Retrying in %.1fs… (%d/%d)",
                exc,
                sleep_for,
                attempt,
                max_retries,
            )
            time.sleep(sleep_for)
