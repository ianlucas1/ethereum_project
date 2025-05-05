# tests/test_utils_api_helpers_error.py

# Add MagicMock to imports
from unittest.mock import patch, MagicMock

import pytest
import requests

# Import the session object we need to patch
from src.utils.api_helpers import robust_get


@patch("src.utils.api_helpers.session.get")
# Add type hint for the mock argument
def test_robust_get_non_200(mock_session_get: MagicMock) -> None:
    """A non-200 HTTP response should raise HTTPError after session retries."""

    # Craft a ``requests.Response`` double that mimics a 5xx server failure.
    bad = MagicMock(spec=requests.Response)
    bad.status_code = 500
    bad.reason = "Internal Server Error"
    bad.url = "http://fail.example"
    bad.text = "boom"
    # Configure the mock raise_for_status to raise the specific error
    http_error = requests.exceptions.HTTPError(
        f"{bad.status_code} Server Error: {bad.reason} for url: {bad.url}", response=bad
    )
    # Set the side_effect on the *mocked session.get* call
    mock_session_get.side_effect = http_error

    # Expect the specific exception raised by raise_for_status after retries
    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        robust_get("http://fail.example")

    # Verify the mocked session.get was called.
    assert mock_session_get.call_count == 1

    # Optional: Check the exception message contains the status code
    assert str(bad.status_code) in str(excinfo.value)
