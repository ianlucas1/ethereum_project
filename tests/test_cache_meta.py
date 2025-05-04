from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.utils import settings
from src.utils import disk_cache


def _monkeypatch_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point settings.DATA_DIR to a temporary directory for isolation."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path, raising=True)
    return tmp_path


def test_series_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _monkeypatch_data_dir(monkeypatch, tmp_path)

    # --- create a cached function returning a Series ---
    calls = {"n": 0}

    @disk_cache("series.parquet", max_age_hr=24)
    def produce_series() -> pd.Series:  # noqa: D401
        """Return a simple Series."""
        calls["n"] += 1
        return pd.Series([1, 2, 3], name="x")

    # first call -> compute & cache
    s1 = produce_series()
    cache_path = tmp_path / "series.parquet"
    meta_path = cache_path.with_suffix(".meta.json")

    assert calls["n"] == 1
    assert cache_path.exists() and meta_path.exists()

    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["pandas_type"] == "Series"

    # second call -> load from cache (no new compute)
    s2 = produce_series()
    assert calls["n"] == 1
    assert s2.equals(s1)


def test_missing_meta_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _monkeypatch_data_dir(monkeypatch, tmp_path)

    @disk_cache("df.parquet", max_age_hr=24)
    def produce_df() -> pd.DataFrame:  # noqa: D401
        return pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    # create cache + meta
    df1 = produce_df()
    cache_path = tmp_path / "df.parquet"
    meta_path = cache_path.with_suffix(".meta.json")
    assert meta_path.exists()

    # remove meta to simulate legacy cache
    meta_path.unlink()

    # should still load correctly (fallback path)
    df2 = produce_df()
    assert df2.equals(df1)
