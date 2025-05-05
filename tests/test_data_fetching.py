# tests/test_data_fetching.py

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_series_equal
from requests.exceptions import RequestException

# Assuming src is importable via conftest.py
from src.config import settings
from src.data_fetching import (
    cm_fetch,
    fetch_eth_price_rapidapi,
    fetch_nasdaq,
)

# --- Fixtures ---


@pytest.fixture(autouse=True)
def manage_fetch_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Fixture to manage cache directory and settings for data fetching tests."""
    test_cache_dir = tmp_path / "fetch_cache"
    test_cache_dir.mkdir()
    monkeypatch.setattr(settings, "DATA_DIR", test_cache_dir)
    monkeypatch.setattr(settings, "RAPIDAPI_KEY", "dummy-rapidapi-key")
    monkeypatch.setattr(settings, "CM_API_KEY", "dummy-cm-key")
    yield test_cache_dir


# --- Fixtures for YF API (Shared by ETH and NASDAQ) ---
@pytest.fixture
def mock_yf_success_response() -> dict:
    """Provides a sample successful JSON response structure for YF chart."""
    # Using different values for clarity vs ETH fixture
    return {
        "chart": {
            "result": [
                {
                    "timestamp": [
                        int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
                        int(datetime(2023, 1, 2, tzinfo=timezone.utc).timestamp()),
                        int(datetime(2023, 1, 3, tzinfo=timezone.utc).timestamp()),
                    ],
                    "indicators": {
                        "quote": [
                            {
                                "close": [15000.50, 15100.75, None],  # NASDAQ values
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


@pytest.fixture
def mock_yf_api_error_response() -> dict:
    """Provides a sample error response structure from YF API."""
    return {
        "chart": {
            "result": None,
            "error": {
                "code": "Bad Request",
                "description": "Symbol ^NDX not found or invalid range",  # NASDAQ specific
            },
        }
    }


@pytest.fixture
def mock_yf_no_data_response() -> dict:
    """Provides a sample 'no data' response structure from YF API."""
    return {
        "chart": {
            "result": None,
            "error": {
                "code": "Not Found",
                "description": "No data found for ^NDX",  # NASDAQ specific
            },
        }
    }


@pytest.fixture
def mock_yf_malformed_response() -> dict:
    """Provides a malformed response (missing expected keys)."""
    return {
        "chart": {
            "result": [
                {
                    # Missing 'timestamp' or 'indicators'
                }
            ],
            "error": None,
        }
    }


# --- Fixtures for cm_fetch ---
@pytest.fixture
def mock_cm_success_page1() -> dict:
    """Mock CM API response - page 1."""
    return {
        "data": [
            {"time": "2023-01-01T00:00:00Z", "AdrActCnt": "1000"},
            {"time": "2023-01-02T00:00:00Z", "AdrActCnt": "1100"},
        ],
        "next_page_url": "http://fake.cm.api/page2",
    }


@pytest.fixture
def mock_cm_success_page2() -> dict:
    """Mock CM API response - page 2."""
    return {
        "data": [
            {"time": "2023-01-03T00:00:00Z", "AdrActCnt": "1050"},
            {"time": "2023-01-04T00:00:00Z", "AdrActCnt": None},  # Test None value
        ],
        "next_page_url": None,  # Last page
    }


@pytest.fixture
def mock_cm_empty_data_response() -> dict:
    """Mock CM API response with no data."""
    return {"data": [], "next_page_url": None}


@pytest.fixture
def mock_cm_malformed_data_response() -> dict:
    """Mock CM API response with malformed data (not a list)."""
    return {"data": "this is not a list", "next_page_url": None}


# --- Tests for fetch_eth_price_rapidapi ---
# (These tests remain unchanged from the previous version)
@patch("src.data_fetching.robust_get")
def test_fetch_eth_price_happy_path(
    mock_robust_get: MagicMock,
    mock_yf_success_response: dict,  # Reusing the YF fixture structure
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.return_value = (
        mock_yf_success_response  # Using YF success structure
    )
    df_result = fetch_eth_price_rapidapi()
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.columns == ["price_usd"]
    assert len(df_result) == 2
    assert isinstance(df_result.index, pd.DatetimeIndex)
    assert df_result.index.tz is None
    expected_index = pd.to_datetime(["2023-01-01", "2023-01-02"])
    # Using values from mock_yf_success_response
    expected_values = [15000.50, 15100.75]
    pd.testing.assert_index_equal(df_result.index, expected_index)
    assert_series_equal(
        df_result["price_usd"],
        pd.Series(expected_values, index=expected_index, name="price_usd"),
        check_dtype=False,
        check_names=False,  # Allow name mismatch as mock is generic YF
    )
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "eth_price_yf.parquet"
    assert cache_file.exists()
    meta_file = manage_fetch_cache_dir / "eth_price_yf.meta.json"
    assert meta_file.exists()


@patch("src.data_fetching.robust_get")
def test_fetch_eth_price_api_error(
    mock_robust_get: MagicMock,
    mock_yf_api_error_response: dict,
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.return_value = mock_yf_api_error_response
    df_result = fetch_eth_price_rapidapi()
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty
    assert df_result.columns == ["price_usd"]
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "eth_price_yf.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty


@patch("src.data_fetching.robust_get")
def test_fetch_eth_price_no_data(
    mock_robust_get: MagicMock,
    mock_yf_no_data_response: dict,
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.return_value = mock_yf_no_data_response
    df_result = fetch_eth_price_rapidapi()
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty
    assert df_result.columns == ["price_usd"]
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "eth_price_yf.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty


@patch("src.data_fetching.robust_get")
def test_fetch_eth_price_malformed_response(
    mock_robust_get: MagicMock,
    mock_yf_malformed_response: dict,
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.return_value = mock_yf_malformed_response
    df_result = fetch_eth_price_rapidapi()
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty
    assert df_result.columns == ["price_usd"]
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "eth_price_yf.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty


@patch("src.data_fetching.robust_get")
def test_fetch_eth_price_robust_get_exception(
    mock_robust_get: MagicMock, manage_fetch_cache_dir: Path
):
    mock_robust_get.side_effect = RequestException("Network Error")
    df_result = fetch_eth_price_rapidapi()
    assert isinstance(df_result, pd.DataFrame)
    assert df_result.empty
    assert df_result.columns == ["price_usd"]
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "eth_price_yf.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty


# --- Tests for cm_fetch ---
# (These tests remain unchanged from the previous version)
@patch("src.data_fetching.robust_get")
def test_cm_fetch_happy_path_pagination(
    mock_robust_get: MagicMock,
    mock_cm_success_page1: dict,
    mock_cm_success_page2: dict,
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.side_effect = [mock_cm_success_page1, mock_cm_success_page2]
    test_metric = "AdrActCnt"
    test_asset = "eth"
    series_result = cm_fetch(metric=test_metric, asset=test_asset)
    assert isinstance(series_result, pd.Series)
    assert series_result.name == test_metric
    assert len(series_result) == 4
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert series_result.index.tz is None
    expected_index = pd.to_datetime(
        ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]
    )
    expected_index.name = "time"  # Add name to expected index
    expected_values = [1000.0, 1100.0, 1050.0, np.nan]
    expected_series = pd.Series(expected_values, index=expected_index, name=test_metric)
    assert_series_equal(
        series_result, expected_series, check_dtype=False, check_exact=False
    )
    assert mock_robust_get.call_count == 2
    cache_file = manage_fetch_cache_dir / f"cm_{test_asset}_{test_metric}.parquet"
    assert cache_file.exists()
    meta_file = manage_fetch_cache_dir / f"cm_{test_asset}_{test_metric}.meta.json"
    assert meta_file.exists()


@patch("src.data_fetching.robust_get")
def test_cm_fetch_empty_data(
    mock_robust_get: MagicMock,
    mock_cm_empty_data_response: dict,
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.return_value = mock_cm_empty_data_response
    test_metric = "FeeTotNtv"
    series_result = cm_fetch(metric=test_metric)
    assert isinstance(series_result, pd.Series)
    assert series_result.name == test_metric
    assert series_result.empty
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert mock_robust_get.call_count == 1
    cache_file = manage_fetch_cache_dir / f"cm_eth_{test_metric}.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty
    assert df_cached.columns == [test_metric]


@patch("src.data_fetching.robust_get")
def test_cm_fetch_malformed_data(
    mock_robust_get: MagicMock,
    mock_cm_malformed_data_response: dict,
    manage_fetch_cache_dir: Path,
):
    mock_robust_get.return_value = mock_cm_malformed_data_response
    test_metric = "TxCnt"
    series_result = cm_fetch(metric=test_metric)
    assert isinstance(series_result, pd.Series)
    assert series_result.name == test_metric
    assert series_result.empty
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert mock_robust_get.call_count == 1
    cache_file = manage_fetch_cache_dir / f"cm_eth_{test_metric}.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty
    assert df_cached.columns == [test_metric]


@patch("src.data_fetching.robust_get")
def test_cm_fetch_robust_get_exception(
    mock_robust_get: MagicMock, manage_fetch_cache_dir: Path
):
    mock_robust_get.side_effect = RequestException("CM Network Error")
    test_metric = "SplyCur"
    series_result = cm_fetch(metric=test_metric)
    assert isinstance(series_result, pd.Series)
    assert series_result.name == test_metric
    assert series_result.empty
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert mock_robust_get.call_count == 1
    cache_file = manage_fetch_cache_dir / f"cm_eth_{test_metric}.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty
    assert df_cached.columns == [test_metric]


# --- Tests for fetch_nasdaq ---


@patch("src.data_fetching.robust_get")
def test_fetch_nasdaq_happy_path(
    mock_robust_get: MagicMock,
    mock_yf_success_response: dict,  # Can reuse YF success structure
    manage_fetch_cache_dir: Path,
):
    """Tests successful fetching and parsing of NASDAQ data."""
    mock_robust_get.return_value = mock_yf_success_response
    series_result = fetch_nasdaq()

    # Assertions
    assert isinstance(series_result, pd.Series)
    assert series_result.name == "nasdaq"
    assert len(series_result) == 2  # Excludes None from mock response
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert series_result.index.tz is None

    # Check specific values (using values from shared YF mock response)
    expected_index = pd.to_datetime(["2023-01-01", "2023-01-02"])
    expected_values = [15000.50, 15100.75]
    expected_series = pd.Series(expected_values, index=expected_index, name="nasdaq")
    assert_series_equal(series_result, expected_series, check_dtype=False)

    # Check robust_get was called (might be multiple times due to chunking)
    assert mock_robust_get.call_count >= 1
    # Check cache file was created
    cache_file = manage_fetch_cache_dir / "nasdaq_ndx.parquet"
    assert cache_file.exists()
    meta_file = manage_fetch_cache_dir / "nasdaq_ndx.meta.json"
    assert meta_file.exists()


@patch("src.data_fetching.robust_get")
def test_fetch_nasdaq_api_error(
    mock_robust_get: MagicMock,
    mock_yf_api_error_response: dict,  # Reuse YF error fixture
    manage_fetch_cache_dir: Path,
):
    """Tests handling of explicit API errors for NASDAQ fetch."""
    mock_robust_get.return_value = mock_yf_api_error_response
    series_result = fetch_nasdaq()

    assert isinstance(series_result, pd.Series)
    assert series_result.name == "nasdaq"
    assert series_result.empty  # Should return empty series on error
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert mock_robust_get.call_count >= 1

    # Cache file should exist and contain empty series
    cache_file = manage_fetch_cache_dir / "nasdaq_ndx.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)  # Read as DataFrame
    assert df_cached.empty
    assert df_cached.columns == ["nasdaq"]


@patch("src.data_fetching.robust_get")
def test_fetch_nasdaq_no_data(
    mock_robust_get: MagicMock,
    mock_yf_no_data_response: dict,  # Reuse YF no data fixture
    manage_fetch_cache_dir: Path,
):
    """Tests handling of 'no data found' API responses for NASDAQ."""
    mock_robust_get.return_value = mock_yf_no_data_response
    series_result = fetch_nasdaq()

    assert isinstance(series_result, pd.Series)
    assert series_result.name == "nasdaq"
    assert series_result.empty
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "nasdaq_ndx.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty
    assert df_cached.columns == ["nasdaq"]


@patch("src.data_fetching.robust_get")
def test_fetch_nasdaq_robust_get_exception(
    mock_robust_get: MagicMock, manage_fetch_cache_dir: Path
):
    """Tests handling when robust_get raises an exception during NASDAQ fetch."""
    mock_robust_get.side_effect = RequestException("NASDAQ Network Error")
    series_result = fetch_nasdaq()

    assert isinstance(series_result, pd.Series)
    assert series_result.name == "nasdaq"
    assert series_result.empty
    assert isinstance(series_result.index, pd.DatetimeIndex)
    assert mock_robust_get.call_count >= 1
    cache_file = manage_fetch_cache_dir / "nasdaq_ndx.parquet"
    assert cache_file.exists()
    df_cached = pd.read_parquet(cache_file)
    assert df_cached.empty
    assert df_cached.columns == ["nasdaq"]
