import json
from pathlib import Path


from src.utils.api_helpers import _save_api_snapshot


def test_save_api_snapshot_creates_timestamped_file(tmp_path: Path):
    """Helper should write exactly one JSON file with the expected prefix and contents."""

    data = {"a": 1}

    _save_api_snapshot(tmp_path, "myprefix", data)

    # After the call, there should be *one* file matching the prefix pattern.
    files = list(tmp_path.glob("myprefix_*.json"))

    assert len(files) == 1, "Snapshot helper did not create exactly one file."

    # Its contents must round-trip back to the original data.
    with files[0].open() as f:
        assert json.load(f) == data
