# tests/test_cache_freshness.py

import os
import time
from datetime import timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Assuming src is importable via conftest.py
from src.config import settings
from src.utils import disk_cache

# --- Test Setup ---

# Define a simple function that uses the disk_cache decorator
# We'll patch its internal _logic_marker to see if it gets called.
_logic_marker = MagicMock()


@disk_cache("test_cache_dummy.parquet", max_age_hr=1)
def _dummy_cached_function(run_id: int) -> pd.DataFrame:
    """A simple function to test caching."""
    _logic_marker(run_id)  # Track calls to the actual logic
    return pd.DataFrame(
        {"data": [run_id], "timestamp": [pd.Timestamp.now(tz=timezone.utc)]}
    )


# --- Test Cases ---


@pytest.fixture(autouse=True)
def manage_cache_dir(tmp_path, monkeypatch):
    """Fixture to manage cache directory and settings for tests."""
    # Use tmp_path for isolated cache
    test_cache_dir = tmp_path / "test_cache"
    test_cache_dir.mkdir()
    # Patch settings.DATA_DIR to use this temporary directory
    monkeypatch.setattr(settings, "DATA_DIR", test_cache_dir)
    # Reset the logic marker before each test
    _logic_marker.reset_mock()
    yield test_cache_dir  # Provide the path to the test if needed
    # Teardown: Clean up the temporary cache directory (handled by tmp_path)


def test_cache_hit(manage_cache_dir):
    """Test that a second call within max_age hits the cache."""
    # Call 1: Should execute the function logic
    result1 = _dummy_cached_function(run_id=1)
    _logic_marker.assert_called_once_with(1)
    _logic_marker.reset_mock()  # Reset mock for the next call

    # Call 2 (immediately after): Should hit cache, logic not called again
    result2 = _dummy_cached_function(run_id=1)  # Use same run_id
    _logic_marker.assert_not_called()

    # Assert results are consistent (or load from cache is correct)
    pd.testing.assert_frame_equal(
        result1, result2, check_dtype=False
    )  # Timestamps might differ slightly if not cached perfectly

    # Check that the cache file exists
    cache_file = manage_cache_dir / "test_cache_dummy.parquet"
    assert cache_file.exists()


def test_cache_refresh_after_max_age(manage_cache_dir):
    """Test that the cache refreshes if the file is older than max_age."""
    cache_file = manage_cache_dir / "test_cache_dummy.parquet"
    max_age_seconds = 1 * 3600  # Corresponds to max_age_hr=1 in decorator

    # Call 1: Create the cache file
    result1 = _dummy_cached_function(run_id=10)
    _logic_marker.assert_called_once_with(10)
    assert cache_file.exists()
    _logic_marker.reset_mock()

    # Modify mtime to be older than max_age
    current_time = time.time()
    past_mtime = (
        current_time - max_age_seconds - 60
    )  # Make it 1 minute older than max age
    os.utime(cache_file, (past_mtime, past_mtime))  # Set both atime and mtime

    # Call 2: Should miss cache due to age, logic should run again
    result2 = _dummy_cached_function(run_id=10)  # Use same run_id
    _logic_marker.assert_called_once_with(10)  # Logic should have been called again

    # Optional: Assert results are different (e.g., timestamp changed)
    # This depends on the function logic; here timestamps should differ.
    assert result1["timestamp"].iloc[0] != result2["timestamp"].iloc[0]

    # Check mtime was updated after refresh
    new_mtime = cache_file.stat().st_mtime
    assert new_mtime > past_mtime  # New mtime should be more recent


# (Test cases will be added here)
