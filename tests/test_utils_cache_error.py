from pathlib import Path

from src.config import settings
from src.utils import disk_cache


def test_disk_cache_rejects_scalar(tmp_path: Path, monkeypatch):
    """disk_cache should *not* attempt to write scalars (unsupported)."""

    # Point the cache directory to a temp dir so no real files are touched.
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)

    @disk_cache("scalar.parquet")
    def gives_scalar():
        return 42  # Not a pandas object => unsupported

    result = gives_scalar()

    # The decorator should simply return the scalar and *not* create a cache file.
    assert result == 42
    assert not (tmp_path / "scalar.parquet").exists()
