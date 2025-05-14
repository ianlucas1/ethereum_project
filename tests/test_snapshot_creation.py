# tests/test_snapshot_creation.py

import json
from pathlib import Path

# Add MagicMock to imports
from unittest.mock import MagicMock, patch

# Add pytest and Path for type hints
import pytest
import requests

# Assuming src is importable due to conftest.py or PYTHONPATH setup
from src.utils.api_helpers import robust_get

# Define mock API response data
MOCK_API_DATA = {
    "data": [
        {"time": "2023-01-01T00:00:00Z", "Value": "100"},
        {"time": "2023-01-02T00:00:00Z", "Value": "110"},
    ],
    "next_page_url": None,
}


@patch("src.utils.api_helpers._save_api_snapshot")
@patch("src.utils.api_helpers.session.get")
# Add type hints for all arguments
def test_robust_get_snapshot_call(
    mock_session_get: MagicMock,
    mock_save_snapshot: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Tests that robust_get calls _save_api_snapshot with correct arguments
    when a snapshot_dir is provided, using the session.
    """
    # 1. Mock snapshot directory
    snapshot_dir = tmp_path / "snapshots"

    # 2. Mock session.get to return a controlled response
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_DATA
    mock_response.content = json.dumps(MOCK_API_DATA).encode("utf-8")
    mock_response.raise_for_status.return_value = None
    mock_session_get.return_value = mock_response

    # 3. Call robust_get directly
    test_url = "http://fake.api/data"
    test_prefix = "custom_prefix"
    result_data = robust_get(
        url=test_url, snapshot_dir=snapshot_dir, snapshot_prefix=test_prefix
    )

    # 4. Assertions on the result and mock calls
    assert result_data == MOCK_API_DATA
    mock_session_get.assert_called_once()
    mock_save_snapshot.assert_called_once()

    call_args, call_kwargs = mock_save_snapshot.call_args
    assert call_args[0] == snapshot_dir
    assert call_args[1] == test_prefix
    assert call_args[2] == MOCK_API_DATA
