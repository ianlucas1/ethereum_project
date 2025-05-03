# tests/test_snapshot_creation.py

import pytest
import requests
import json
from pathlib import Path
from unittest.mock import MagicMock, patch # For mocking requests.Response and patching

# Assuming src is importable due to conftest.py or PYTHONPATH setup
from src.config import settings
# from src.data_fetching import cm_fetch # Use cm_fetch as an example fetcher
from src.utils import robust_get # <-- Import directly

# Define mock API response data
MOCK_API_DATA = {
    "data": [
        {"time": "2023-01-01T00:00:00Z", "Value": "100"}, # Changed key for variety
        {"time": "2023-01-02T00:00:00Z", "Value": "110"},
    ],
    "next_page_url": None,
}

# Target the function *where it's looked up* (in src.utils module)
@patch('src.utils._save_api_snapshot')
def test_robust_get_snapshot_call(mock_save_snapshot, monkeypatch, tmp_path):
    """
    Tests that robust_get calls _save_api_snapshot with correct arguments
    when a snapshot_prefix is provided, by calling robust_get directly.
    """
    # 1. Mock snapshot directory (DATA_DIR mocking not needed for this test)
    snapshot_dir = tmp_path / "snapshots"
    monkeypatch.setattr(settings, 'RAW_SNAPSHOT_DIR', snapshot_dir)

    # 2. Mock requests.get to return a controlled response
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_DATA
    mock_response.content = json.dumps(MOCK_API_DATA).encode('utf-8')
    def mock_get(*args, **kwargs):
        mock_response.raise_for_status()
        return mock_response
    monkeypatch.setattr(requests, "get", mock_get)

    # 3. Call robust_get directly
    test_url = "http://fake.api/data"
    test_prefix = "test_snapshot_prefix"
    result_data = robust_get(url=test_url, snapshot_prefix=test_prefix)

    # 4. Assertions on the *mock* object and result
    # a) Check the returned data is correct
    assert result_data == MOCK_API_DATA, "robust_get did not return the expected data."

    # b) Check if _save_api_snapshot was called exactly once
    mock_save_snapshot.assert_called_once()

    # c) Check the arguments it was called with
    call_args, call_kwargs = mock_save_snapshot.call_args
    # call_args is a tuple: (directory, filename_prefix, data)
    assert call_args[0] == snapshot_dir, "Snapshot helper not called with correct directory."
    assert call_args[1] == test_prefix, "Snapshot helper not called with correct prefix."
    assert call_args[2] == MOCK_API_DATA, "Snapshot helper not called with correct data." 