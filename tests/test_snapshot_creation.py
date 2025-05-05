# tests/test_snapshot_creation.py

import json
from unittest.mock import MagicMock, patch  # For mocking requests.Response and patching

import requests

# Assuming src is importable due to conftest.py or PYTHONPATH setup
from src.utils.api_helpers import robust_get  # <-- Import directly

# Define mock API response data
MOCK_API_DATA = {
    "data": [
        {"time": "2023-01-01T00:00:00Z", "Value": "100"},  # Changed key for variety
        {"time": "2023-01-02T00:00:00Z", "Value": "110"},
    ],
    "next_page_url": None,
}


# Target the function *where it's looked up* (in src.utils.api_helpers module)
@patch("src.utils.api_helpers._save_api_snapshot")  # CORRECTED PATCH TARGET
def test_robust_get_snapshot_call(mock_save_snapshot, monkeypatch, tmp_path):
    """
    Tests that robust_get calls _save_api_snapshot with correct arguments
    when a snapshot_dir is provided, by calling robust_get directly.
    """
    # 1. Mock snapshot directory (DATA_DIR mocking not needed for this test)
    snapshot_dir = tmp_path / "snapshots"
    # Note: monkeypatching settings.RAW_SNAPSHOT_DIR is not strictly necessary
    # for this test as we pass snapshot_dir directly to robust_get,
    # but it's good practice if other parts relied on it.
    # monkeypatch.setattr(settings, "RAW_SNAPSHOT_DIR", snapshot_dir) # Keep or remove as needed

    # 2. Mock requests.get to return a controlled response
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_API_DATA
    mock_response.content = json.dumps(MOCK_API_DATA).encode("utf-8")

    def mock_get(*args, **kwargs):
        # No need to call raise_for_status in the mock if status is 200
        # mock_response.raise_for_status()
        return mock_response

    monkeypatch.setattr(requests, "get", mock_get)

    # 3. Call robust_get directly
    test_url = "http://fake.api/data"
    # test_prefix = "test_snapshot_prefix" # Not used directly by robust_get
    result_data = robust_get(
        url=test_url, snapshot_dir=snapshot_dir
    )  # Pass snapshot_dir

    # 4. Assertions on the *mock* object and result
    # a) Check the returned data is correct
    assert result_data == MOCK_API_DATA, "robust_get did not return the expected data."

    # b) Check if _save_api_snapshot was called exactly once
    mock_save_snapshot.assert_called_once()

    # c) Check the arguments it was called with
    call_args, call_kwargs = mock_save_snapshot.call_args
    # call_args is a tuple: (directory, filename_prefix, data)
    assert call_args[0] == snapshot_dir, (
        "Snapshot helper not called with correct directory."
    )
    assert (
        call_args[1] == "api_snapshot"
    ), (  # CORRECTED ASSERTION: Check hardcoded prefix
        "Snapshot helper not called with correct prefix 'api_snapshot'."
    )
    assert call_args[2] == MOCK_API_DATA, (
        "Snapshot helper not called with correct data."
    )
