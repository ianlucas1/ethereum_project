from pathlib import Path

import pandas as pd
import pytest

# Import the loader under test
from src.utils.file_io import load_parquet


def test_load_parquet_index_fallback(tmp_path: Path):
    """Data saved with the wrong index name should be reset/renamed by loader."""

    # Location where the temporary parquet will be written
    p = tmp_path / "weird.parquet"

    # Create a DataFrame whose *index* already holds the timestamps, but the index
    # is *named* something other than "time" – this exercises the fallback branch
    # inside ``load_parquet`` where it must reset the index and rename the first
    # column to the canonical ``time`` label before setting it back as the index.
    df = pd.DataFrame({"value": [10, 20, 30]})
    df.index = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"])
    df.index.name = "not_time"

    # Persist to parquet so that the loader has to perform a full round-trip
    df.to_parquet(p)

    # ─── Exercise & verify ────────────────────────────────────────────────────
    out = load_parquet(p)

    # The loader should promote the index to a proper ``DatetimeIndex`` named
    # ``time``.  The underlying values as well as the column data should remain
    # unchanged.
    assert isinstance(out.index, pd.DatetimeIndex)
    assert out.index.name == "time"

    # Build an *expected* DataFrame that mirrors the format that the loader
    # should output – namely, the *same* values but with the index correctly
    # labelled as ``time``.
    expected = df.rename_axis("time")

    pd.testing.assert_frame_equal(out, expected)


# ---------------------------------------------------------------------------
# Missing column validation
# ---------------------------------------------------------------------------


def test_load_parquet_missing_columns(tmp_path: Path):
    """If *any* columns requested via ``req_cols`` are absent, a ValueError is raised."""

    path = tmp_path / "mini.parquet"

    # Frame contains the mandatory 'time' plus only one of the required cols.
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(["2024-01-01"]),
            "x": [1],
        }
    )
    df.to_parquet(path)

    with pytest.raises(ValueError, match=r"missing required columns.*\['y'\]"):
        load_parquet(path, req_cols=["x", "y"])
