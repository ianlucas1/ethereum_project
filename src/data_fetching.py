"""Functions for fetching raw data from external APIs.

Handles fetching data from:
- Yahoo Finance (via RapidAPI) for ETH price and NASDAQ index.
- CoinMetrics Community API for various on-chain metrics.

Includes robust error handling, request retries (via session),
and disk caching to avoid redundant downloads.
"""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

# Import settings and helpers
from src.config import settings

from .utils import disk_cache, robust_get  # Remove DATA_DIR import

# --- Data Fetching Functions ---


# Note: The disk_cache decorator needs to be aware of settings.DATA_DIR
# We assume the implementation of disk_cache uses settings.DATA_DIR
# For simplicity, the cache filename passed here remains relative
@disk_cache("eth_price_yf.parquet", max_age_hr=24)
def fetch_eth_price_rapidapi() -> pd.DataFrame:
    """Fetches daily ETH-USD close from Yahoo via RapidAPI (chunked).

    Uses disk caching defined in utils.py (assumed to use settings.DATA_DIR).

    Returns:
        pd.DataFrame: A DataFrame with a single 'price_usd' column and DatetimeIndex.
                      Returns an empty DataFrame if fetching fails completely.
    """
    key = settings.RAPIDAPI_KEY
    if not key:
        logging.error("RAPIDAPI_KEY not found in settings.")
        raise ValueError("RAPIDAPI_KEY not configured in settings")

    host = "apidojo-yahoo-finance-v1.p.rapidapi.com"
    url = f"https://{host}/stock/v2/get-chart"
    hdrs = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}

    # YF API reported firstTradeDate around here for ETH-USD
    start = datetime(2017, 11, 9).date()
    today = datetime.now(tz=timezone.utc).date()
    pieces: list[pd.Series] = []  # Type hint for list of Series
    logging.info("Starting Yahoo Finance ETH price fetch from %s to %s", start, today)

    while start <= today:
        end = min(start + timedelta(days=364), today)
        try:
            start_ts = int(
                datetime.combine(
                    start, datetime.min.time(), tzinfo=timezone.utc
                ).timestamp()
            )
            end_ts = int(
                datetime.combine(
                    end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
                ).timestamp()
            )
        except (OverflowError, OSError) as ts_err:
            logging.error(
                f"Timestamp conversion error for dates {start} to {end}: {ts_err}. Skipping chunk."
            )
            start = end + timedelta(days=1)
            continue

        params = {
            "symbol": "ETH-USD",
            "interval": "1d",
            "period1": start_ts,
            "period2": end_ts,
        }
        logging.debug(f"Fetching YF ETH: start={start}, end={end}, params={params}")
        response_json = None
        try:
            # Use robust_get imported from utils
            prefix = f"yf_eth_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
            # robust_get returns dict[str, Any], which is compatible with Json type alias
            response_json = robust_get(
                url, headers=hdrs, params=params, snapshot_prefix=prefix
            )

            # Defensive parsing checks (ensure structure is as expected)
            chart_data = response_json.get("chart", {})
            chart_result = chart_data.get("result")
            chart_error = chart_data.get("error")

            if chart_error or chart_result is None:
                error_desc = (
                    chart_error.get("description", "Result is null")
                    if chart_error
                    else "Result is null"
                )
                if "Data doesn't exist" in error_desc or "No data found" in error_desc:
                    logging.info(
                        f"YF ETH API reported no data for {start} to {end}: {error_desc}"
                    )
                else:
                    logging.error(
                        f"YF ETH API Error for {start} to {end}: {error_desc}"
                    )
                start = end + timedelta(days=1)
                continue

            if not isinstance(chart_result, list) or not chart_result:
                logging.warning(
                    f"YF ETH API 'result' is not a non-empty list for {start} to {end}. Skipping. Result: {str(chart_result)[:200]}..."
                )
                start = end + timedelta(days=1)
                continue

            result_data = chart_result[0]
            timestamps = result_data.get("timestamp")
            indicators = result_data.get("indicators")

            if timestamps is None or indicators is None:
                logging.warning(
                    f"Missing 'timestamp' or 'indicators' in YF ETH API result[0] for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            quote = indicators.get("quote")
            if not quote or not isinstance(quote, list) or not quote[0]:
                logging.warning(
                    f"Missing 'quote' array in YF ETH API indicators for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            close_prices = quote[0].get("close")
            if close_prices is None:
                logging.warning(
                    f"Missing 'close' prices in YF ETH API quote[0] for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            if not isinstance(timestamps, list) or not isinstance(close_prices, list):
                logging.warning(
                    f"Timestamps or close_prices are not lists for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            if len(close_prices) != len(timestamps):
                logging.warning(
                    f"Mismatch length for close/timestamps in YF ETH API response for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            # Create Series, ensuring index matches non-null data points
            valid_indices = [
                i for i, price in enumerate(close_prices) if price is not None
            ]
            if not valid_indices:
                logging.info(
                    f"No valid (non-null) ETH price data found for chunk {start} to {end}."
                )
            else:
                valid_timestamps = [timestamps[i] for i in valid_indices]
                valid_prices = [close_prices[i] for i in valid_indices]

                series_data = pd.Series(
                    valid_prices,
                    index=pd.to_datetime(valid_timestamps, unit="s", utc=True)
                    .tz_convert(None)
                    .normalize(),
                    name="price_usd",
                )
                pieces.append(series_data)
                logging.debug(
                    f"Successfully processed YF ETH chunk {start} to {end}, got {len(series_data)} data points."
                )

        except (
            RuntimeError,
            requests.exceptions.RequestException,
            json.JSONDecodeError,
            ValueError,  # Catch potential ValueError from robust_get if JSON is invalid
        ) as req_err:
            # Errors from robust_get or parsing issues already logged by robust_get or above checks
            logging.error(
                f"Handled error during YF ETH fetch/parse for chunk {start} to {end}: {req_err}. Skipping chunk."
            )
        except Exception as e:
            logging.error(
                f"Unexpected error processing YF ETH chunk {start} to {end}: {e}",
                exc_info=True,
            )
        finally:
            # Ensure 'start' is always incremented
            start = end + timedelta(days=1)
            # Add a small delay to avoid hitting rate limits
            time.sleep(random.uniform(0.2, 0.5))

    if not pieces:
        logging.error("No ETH price data pieces were collected from Yahoo Finance API.")
        # Return an empty DataFrame with the correct structure if no data is fetched
        return pd.DataFrame(columns=["price_usd"], index=pd.to_datetime([]))
        # Or raise: raise RuntimeError("No ETH data successfully fetched from Yahoo Finance API.")

    logging.info(
        "Finished Yahoo Finance ETH fetch. Concatenating %d pieces.", len(pieces)
    )
    eth_df = (
        pd.concat(pieces).sort_index().loc[lambda s: ~s.index.duplicated()]
    )  # De-duplicate just in case

    # Ensure final result index is timezone-naive (should be handled by disk_cache too)
    if (
        pd.api.types.is_datetime64_any_dtype(eth_df.index)
        and eth_df.index.tz is not None
    ):
        eth_df.index = eth_df.index.tz_localize(None)

    # Ensure cache path is correct in the disk_cache decorator logic
    # Example: The decorator should internally use settings.DATA_DIR / cache_filename
    # Here, we return the DataFrame. The decorator handles saving to settings.DATA_DIR / "eth_price_yf.parquet"
    return eth_df.to_frame()  # Ensure return is DataFrame


@disk_cache(
    "cm_{asset}_{metric}.parquet", max_age_hr=24
)  # Dynamic name passed to decorator
def cm_fetch(
    metric: str, asset: str = "eth", start: str = "2015-08-01", freq: str = "1d"
) -> pd.Series:
    """Fetches a specific metric from CoinMetrics Community API.

    Uses disk caching defined in utils.py (assumed to use settings.DATA_DIR).
    Cache filename includes asset and metric dynamically handled by the decorator.

    Args:
        metric (str): The CoinMetrics metric ID (e.g., 'AdrActCnt').
        asset (str): The asset ID (default: 'eth').
        start (str): Start date in 'YYYY-MM-DD' format (default: '2015-08-01').
        freq (str): Data frequency ('1d', '1h', etc.) (default: '1d').

    Returns:
        pd.Series: A Series containing the metric data with DatetimeIndex.
                   Returns an empty Series if fetching fails.
    """
    # The cache filename is handled dynamically by the decorator based on args.
    # The decorator should construct the full path using settings.DATA_DIR.

    base = (
        f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
        f"?assets={asset}&metrics={metric}&frequency={freq}"
        f"&start_time={start}&page_size=10000"
    )
    hdr: dict[str, str] = {}  # Type hint for header dict
    api_key = settings.CM_API_KEY  # Use settings
    if api_key:
        hdr["Authorization"] = f"Bearer {api_key}"
        logging.info(f"Using CoinMetrics API Key for metric: {metric}")
    else:
        logging.info(f"Fetching CoinMetrics data without API key for metric: {metric}")

    data: list[dict[str, str]] = []  # Type hint for list of dicts
    url: str | None = base  # Type hint for url (can be None)
    page_count = 0
    while url:
        page_count += 1
        logging.debug(f"Fetching CM page {page_count}: {url.split('?')[0]}...")
        try:
            # Use robust_get imported from utils
            prefix = f"cm_{asset}_{metric}_p{page_count}"
            j = robust_get(url, headers=hdr, snapshot_prefix=prefix)
            page_data = j.get("data", [])
            if not isinstance(page_data, list):
                logging.warning(
                    f"CM API 'data' field is not a list on page {page_count} for {metric}. Skipping page."
                )
                url = j.get("next_page_url")  # Still try next page
                continue

            # Basic check: Ensure items in page_data are dictionaries
            if page_data and not all(isinstance(item, dict) for item in page_data):
                logging.warning(
                    f"CM API 'data' items are not all dictionaries on page {page_count} for {metric}. Skipping page."
                )
                url = j.get("next_page_url")  # Still try next page
                continue

            data.extend(page_data)  # Now safe to extend
            url = j.get("next_page_url")
            # Add a small delay to be polite to the API
            if url:
                time.sleep(random.uniform(0.5, 1.5))
        except (
            RuntimeError,
            requests.exceptions.RequestException,
            json.JSONDecodeError,
            ValueError,  # Catch potential ValueError from robust_get
        ) as req_err:
            logging.error(
                f"Failed to fetch or parse CM page for {metric}: {req_err}. Stopping fetch."
            )
            url = None  # Stop pagination on error
        except Exception as e:
            logging.error(
                f"Unexpected error fetching CM page for {metric}: {e}", exc_info=True
            )
            url = None  # Stop pagination

    if not data:
        logging.error(f"No data returned from CoinMetrics for metric: {metric}")
        # Return an empty Series with a datetime index
        return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)
        # Or raise: raise RuntimeError(f"No data returned for {metric}")

    logging.info(f"Finished CoinMetrics fetch for {metric}, got {len(data)} records.")
    try:
        # Ensure 'time' and 'metric' columns exist before processing
        if not data or "time" not in data[0] or metric not in data[0]:
            logging.error(
                f"Required columns ('time', '{metric}') not found in first record of CM data."
            )
            return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)

        df_from_data = pd.DataFrame(data)
        # Check columns again after DataFrame creation
        if "time" not in df_from_data.columns or metric not in df_from_data.columns:
            logging.error(
                f"Required columns ('time', '{metric}') not found in CM DataFrame. Columns: {df_from_data.columns.tolist()}"
            )
            return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)

        series = (
            df_from_data.assign(time=lambda d: pd.to_datetime(d["time"]))
            .set_index("time")[metric]
            .astype(float)  # Convert to float *after* selecting the column
            .sort_index()
            .loc[lambda s: ~s.index.duplicated()]
        )  # De-duplicate just in case

        # Ensure index is timezone-naive (should be handled by disk_cache too)
        if (
            pd.api.types.is_datetime64_any_dtype(series.index)
            and series.index.tz is not None
        ):
            series.index = series.index.tz_localize(None)
        return series
    except KeyError:
        logging.error(
            f"Metric '{metric}' not found in CM response columns after DataFrame creation: {pd.DataFrame(data).columns.tolist()}"
        )
        return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)
    except Exception as e:
        logging.error(
            f"Error processing CoinMetrics data for {metric}: {e}", exc_info=True
        )
        return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)


@disk_cache("nasdaq_ndx.parquet", max_age_hr=24)
def fetch_nasdaq() -> pd.Series:
    """Fetches true-daily ^NDX close from Yahoo via RapidAPI (chunked).

    Uses disk caching defined in utils.py (assumed to use settings.DATA_DIR).

    Returns:
        pd.Series: A pandas Series named 'nasdaq' with DatetimeIndex.
                   Returns an empty Series if fetching fails.
    """
    key = settings.RAPIDAPI_KEY  # Use settings
    if not key:
        logging.error("RAPIDAPI_KEY not found in settings.")
        raise ValueError("RAPIDAPI_KEY not configured in settings")

    host = "apidojo-yahoo-finance-v1.p.rapidapi.com"
    url = f"https://{host}/stock/v2/get-chart"
    hdrs = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}

    start = datetime(1985, 1, 1).date()  # Earliest ^NDX on Yahoo
    today = datetime.now(tz=timezone.utc).date()
    pieces: list[pd.Series] = []  # Type hint for list of Series
    logging.info("Starting NASDAQ (^NDX) fetch from %s to %s", start, today)

    while start <= today:
        end = min(start + timedelta(days=364), today)
        try:
            start_ts = int(
                datetime.combine(
                    start, datetime.min.time(), tzinfo=timezone.utc
                ).timestamp()
            )
            end_ts = int(
                datetime.combine(
                    end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
                ).timestamp()
            )
        except (OverflowError, OSError) as ts_err:
            logging.error(
                f"Timestamp conversion error for NASDAQ dates {start} to {end}: {ts_err}. Skipping chunk."
            )
            start = end + timedelta(days=1)
            continue

        params = {
            "symbol": "^NDX",
            "interval": "1d",
            "period1": start_ts,
            "period2": end_ts,
        }
        logging.debug(f"Fetching ^NDX: start={start}, end={end}, params={params}")
        response_json = None
        try:
            # Use robust_get imported from utils
            prefix = f"yf_ndx_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
            response_json = robust_get(
                url, headers=hdrs, params=params, snapshot_prefix=prefix
            )

            # Defensive parsing checks
            chart_data = response_json.get("chart", {})
            chart_result = chart_data.get("result")
            chart_error = chart_data.get("error")

            if chart_error or chart_result is None:
                error_desc = (
                    chart_error.get("description", "Result is null")
                    if chart_error
                    else "Result is null"
                )
                if "Data doesn't exist" in error_desc or "No data found" in error_desc:
                    logging.info(
                        f"^NDX API reported no data for {start} to {end}: {error_desc}"
                    )
                else:
                    logging.error(f"^NDX API Error for {start} to {end}: {error_desc}")
                start = end + timedelta(days=1)
                continue

            if not isinstance(chart_result, list) or not chart_result:
                logging.warning(
                    f"^NDX API 'result' is not a non-empty list for {start} to {end}. Skipping. Result: {str(chart_result)[:200]}..."
                )
                start = end + timedelta(days=1)
                continue

            result_data = chart_result[0]
            timestamps = result_data.get("timestamp")
            indicators = result_data.get("indicators")
            if timestamps is None or indicators is None:
                logging.warning(
                    f"Missing 'timestamp' or 'indicators' in ^NDX API result[0] for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            quote = indicators.get("quote")
            if not quote or not isinstance(quote, list) or not quote[0]:
                logging.warning(
                    f"Missing 'quote' array in ^NDX API indicators for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            close_prices = quote[0].get("close")
            if close_prices is None:
                logging.warning(
                    f"Missing 'close' prices in ^NDX API quote[0] for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            if not isinstance(timestamps, list) or not isinstance(close_prices, list):
                logging.warning(
                    f"Timestamps or close_prices are not lists for NASDAQ {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            if len(close_prices) != len(timestamps):
                logging.warning(
                    f"Mismatch length for close/timestamps in ^NDX API response for {start} to {end}. Skipping."
                )
                start = end + timedelta(days=1)
                continue

            # Create Series, ensuring index matches non-null data points
            valid_indices = [
                i for i, price in enumerate(close_prices) if price is not None
            ]
            if not valid_indices:
                logging.info(
                    f"No valid (non-null) NASDAQ price data found for chunk {start} to {end}."
                )
            else:
                valid_timestamps = [timestamps[i] for i in valid_indices]
                valid_prices = [close_prices[i] for i in valid_indices]
                series_data = pd.Series(
                    valid_prices,
                    index=pd.to_datetime(valid_timestamps, unit="s", utc=True)
                    .tz_convert(None)
                    .normalize(),
                    name="nasdaq",
                )
                pieces.append(series_data)
                logging.debug(
                    f"Successfully processed ^NDX chunk {start} to {end}, got {len(series_data)} data points."
                )

        except (
            RuntimeError,
            requests.exceptions.RequestException,
            json.JSONDecodeError,
            ValueError,  # Catch potential ValueError from robust_get
        ) as req_err:
            logging.error(
                f"Handled error during NASDAQ fetch/parse for chunk {start} to {end}: {req_err}. Skipping chunk."
            )
        except Exception as e:
            logging.error(
                f"Unexpected error processing NASDAQ chunk {start} to {end}: {e}",
                exc_info=True,
            )
        finally:
            # Ensure 'start' is always incremented
            start = end + timedelta(days=1)
            # Add a small delay to avoid hitting rate limits
            time.sleep(random.uniform(0.2, 0.5))

    if not pieces:
        logging.error(
            "No NASDAQ data pieces were collected after processing all chunks."
        )
        # Return an empty Series with the correct structure
        return pd.Series(dtype=float, index=pd.to_datetime([]), name="nasdaq")
        # Or raise: raise RuntimeError("No NASDAQ data successfully fetched after processing all chunks.")

    logging.info("Finished NASDAQ fetch. Concatenating %d pieces.", len(pieces))
    ndx_series = (
        pd.concat(pieces).sort_index().loc[lambda s: ~s.index.duplicated()]
    )  # De-duplicate just in case

    # Ensure final result index is timezone-naive (should be handled by disk_cache too)
    if (
        pd.api.types.is_datetime64_any_dtype(ndx_series.index)
        and ndx_series.index.tz is not None
    ):
        ndx_series.index = ndx_series.index.tz_localize(None)

    return ndx_series
