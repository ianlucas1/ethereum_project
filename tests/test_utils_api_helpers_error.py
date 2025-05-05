from unittest.mock import patch, MagicMock

import pytest
import requests


# Function under test
from src.utils.api_helpers import robust_get


@patch("time.sleep", return_value=None)  # Skip real waits
@patch("requests.get")
def test_robust_get_non_200(mock_get, _sleep):
    """A non-200 HTTP response should be retried ``max_retries`` times then raise."""

    # Craft a ``requests.Response`` double that mimics a 5xx server failure.
    bad = MagicMock(spec=requests.Response)
    bad.status_code = 500
    bad.text = "boom"
    # Configure the mock raise_for_status to raise the specific error
    bad.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Mock HTTP Error", response=bad
    )

    # Each call to ``requests.get`` returns the same failing response so that the
    # retry loop is exercised. We give max_retries=2, so total attempts is 2.
    # The loop runs for attempt=1, attempt=2. On attempt=2, the exception is raised.
    mock_get.side_effect = [bad] * 2  # Need enough mocks for all attempts

    # Expect the specific exception raised by raise_for_status after retries
    with pytest.raises(requests.exceptions.HTTPError):  # CORRECTED EXPECTED EXCEPTION
        robust_get("http://fail.example", max_retries=2)

    # Verify the *number* of network attempts equals max_retries.
    assert mock_get.call_count == 2
