from unittest.mock import patch, MagicMock

import pytest
import requests


# Function under test
from src.utils.api_helpers import robust_get


@patch("time.sleep", return_value=None)  # Skip real waits
@patch("requests.get")
def test_robust_get_non_200(mock_get, _sleep):
    """A non-200 HTTP response should be retried ``retries`` times then raise."""

    # Craft a ``requests.Response`` double that mimics a 5xx server failure.
    bad = MagicMock(spec=requests.Response)
    bad.status_code = 500
    bad.text = "boom"
    bad.raise_for_status.side_effect = requests.exceptions.HTTPError

    # Each call to ``requests.get`` returns the same failing response so that the
    # retry loop is exercised.  We give two retries so total attempts is 1+2=3.
    mock_get.side_effect = [bad] * 2

    with pytest.raises(RuntimeError):
        robust_get("http://fail.example", retries=2)

    # Verify the *number* of network attempts equals the ``retries`` argument.
    assert mock_get.call_count == 2
