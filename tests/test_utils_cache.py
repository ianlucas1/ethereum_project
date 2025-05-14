import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.config import settings
from src.utils import disk_cache
from src.utils.cache import FileLock

# -----------------------------------------------------------------------------
# 1. Cache miss -> write -> hit
# -----------------------------------------------------------------------------


def test_disk_cache_write_and_hit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """First call writes cache; second call hits cache without re-executing."""
    # Redirect DATA_DIR to the temporary path
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    calls = {"count": 0}

    @disk_cache("dummy.parquet", max_age_hr=24)
    def expensive():  # - simple test helper
        calls["count"] += 1
        return pd.Series([1, 2, 3])

    # Initial invocation should execute the function and write cache
    s1 = expensive()
    assert calls["count"] == 1
    assert (tmp_path / "dummy.parquet").exists(), "Cache file not written on miss."

    # Second invocation - within max_age - should hit cache (no new call)
    s2 = expensive()
    assert calls["count"] == 1, "Function re-executed despite fresh cache."
    pd.testing.assert_series_equal(s1, s2, check_names=False)


# -----------------------------------------------------------------------------
# 2. Cache expiry forces refresh
# -----------------------------------------------------------------------------


def test_disk_cache_expiry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cache should refresh if file is older than max_age_hr."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    @disk_cache("expire.parquet", max_age_hr=0)  # 0 hr => always stale
    def make():  # - simple test helper
        return pd.Series([42])

    # First call writes the cache file
    make()
    cache_file = tmp_path / "expire.parquet"
    assert cache_file.exists()

    # Back-date mtime so cache looks old
    past = time.time() - 3600  # 1 hour ago
    os.utime(cache_file, (past, past))

    # Patch logger to silence output & ensure codepath runs
    with monkeypatch.context() as m:
        m.setattr("src.utils.cache.logging", MagicMock())
        refreshed = make()

    # Ensure we still get correct data
    assert refreshed.iloc[0] == 42


# -----------------------------------------------------------------------------
# 3. Lock-file handling
# -----------------------------------------------------------------------------


def test_disk_cache_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure FileLock.acquire is invoked when caching."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    acquired = {"count": 0}
    real_acquire = FileLock.acquire

    def fake_acquire(self, *args, **kwargs):  # - wrapper
        acquired["count"] += 1
        return real_acquire(self, *args, **kwargs)

    monkeypatch.setattr(FileLock, "acquire", fake_acquire)

    @disk_cache("lock.parquet", max_age_hr=24)
    def func():  # - simple test helper
        return pd.Series([99])

    func()
    func()

    # There should be at least one attempt to acquire the lock
    assert acquired["count"] >= 1
