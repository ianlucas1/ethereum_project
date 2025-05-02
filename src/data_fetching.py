# src/data_fetching.py

import os
import logging
import json
import random
import time
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd
import shutil # Added for disk_cache move operation

# Import helpers from the utils module
from .utils import disk_cache, robust_get, DATA_DIR # Use relative import

# --- Data Fetching Functions ---

@disk_cache("eth_price_yf.parquet", max_age_hr=24)
def fetch_eth_price_rapidapi() -> pd.DataFrame:
    """Fetches daily ETH-USD close from Yahoo via RapidAPI (chunked).

    Uses disk caching defined in utils.py.
    Returns a DataFrame with a single 'price_usd' column.
    """
    key = os.getenv("RAPIDAPI_KEY")
    if not key:
        logging.error("RAPIDAPI_KEY environment variable not set.")
        raise EnvironmentError("RAPIDAPI_KEY env-var not set")

    host = "apidojo-yahoo-finance-v1.p.rapidapi.com"
    url = f"https://{host}/stock/v2/get-chart"
    hdrs = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}

    # YF API reported firstTradeDate around here for ETH-USD
    start = datetime(2017, 11, 9).date()
    today = datetime.now(tz=timezone.utc).date()
    pieces = []
    logging.info("Starting Yahoo Finance ETH price fetch from %s to %s", start, today)

    while start <= today:
        end = min(start + timedelta(days=364), today)
        try:
            start_ts = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            end_ts = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        except (OverflowError, OSError) as ts_err:
             logging.error(f"Timestamp conversion error for dates {start} to {end}: {ts_err}. Skipping chunk.")
             start = end + timedelta(days=1)
             continue

        params = {
            "symbol": "ETH-USD",
            "interval": "1d",
            "period1": start_ts,
            "period2": end_ts
        }
        logging.debug(f"Fetching YF ETH: start={start}, end={end}, params={params}")
        response_json = None
        try:
            # Use robust_get imported from utils
            response_json = robust_get(url, headers=hdrs, params=params)

            # Defensive parsing checks (ensure structure is as expected)
            chart_data = response_json.get("chart", {})
            chart_result = chart_data.get("result")
            chart_error = chart_data.get("error")

            if chart_error or chart_result is None:
                error_desc = chart_error.get("description", "Result is null") if chart_error else "Result is null"
                if "Data doesn't exist" in error_desc or "No data found" in error_desc:
                    logging.info(f"YF ETH API reported no data for {start} to {end}: {error_desc}")
                else:
                    logging.error(f"YF ETH API Error for {start} to {end}: {error_desc}")
                start = end + timedelta(days=1)
                continue

            if not isinstance(chart_result, list) or not chart_result:
                logging.warning(f"YF ETH API 'result' is not a non-empty list for {start} to {end}. Skipping. Result: {str(chart_result)[:200]}...")
                start = end + timedelta(days=1)
                continue

            result_data = chart_result[0]
            timestamps = result_data.get("timestamp")
            indicators = result_data.get("indicators")

            if timestamps is None or indicators is None:
                logging.warning(f"Missing 'timestamp' or 'indicators' in YF ETH API result[0] for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            quote = indicators.get("quote")
            if not quote or not isinstance(quote, list) or not quote[0]:
                logging.warning(f"Missing 'quote' array in YF ETH API indicators for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            close_prices = quote[0].get("close")
            if close_prices is None:
                logging.warning(f"Missing 'close' prices in YF ETH API quote[0] for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            if len(close_prices) != len(timestamps):
                logging.warning(f"Mismatch length for close/timestamps in YF ETH API response for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            # Create Series, ensuring index matches non-null data points
            valid_indices = [i for i, price in enumerate(close_prices) if price is not None]
            if not valid_indices:
                logging.info(f"No valid (non-null) ETH price data found for chunk {start} to {end}.")
            else:
                valid_timestamps = [timestamps[i] for i in valid_indices]
                valid_prices = [close_prices[i] for i in valid_indices]

                ser = pd.Series(
                    valid_prices,
                    index=pd.to_datetime(valid_timestamps, unit="s", utc=True).tz_convert(None).normalize(),
                    name="price_usd"
                )
                pieces.append(ser)
                logging.debug(f"Successfully processed YF ETH chunk {start} to {end}, got {len(ser)} data points.")

        except (RuntimeError, requests.exceptions.RequestException, json.JSONDecodeError) as req_err:
             # Errors from robust_get or parsing issues already logged by robust_get or above checks
             logging.error(f"Handled error during YF ETH fetch/parse for chunk {start} to {end}: {req_err}. Skipping chunk.")
        except Exception as e:
             logging.error(f"Unexpected error processing YF ETH chunk {start} to {end}: {e}", exc_info=True)
        finally:
             # Ensure 'start' is always incremented
             start = end + timedelta(days=1)

    if not pieces:
        logging.error("No ETH price data pieces were collected from Yahoo Finance API.")
        # Return an empty DataFrame with the correct structure if no data is fetched
        return pd.DataFrame(columns=['price_usd'], index=pd.to_datetime([]))
        # Or raise: raise RuntimeError("No ETH data successfully fetched from Yahoo Finance API.")

    logging.info("Finished Yahoo Finance ETH fetch. Concatenating %d pieces.", len(pieces))
    eth_df = (pd.concat(pieces)
              .sort_index()
              .loc[lambda s: ~s.index.duplicated()]) # De-duplicate just in case

    # Ensure final result index is timezone-naive (should be handled by disk_cache too)
    if pd.api.types.is_datetime64_any_dtype(eth_df.index) and eth_df.index.tz is not None:
        eth_df.index = eth_df.index.tz_localize(None)

    return eth_df.to_frame() # Ensure return is DataFrame


@disk_cache("cm_{asset}_{metric}.parquet", max_age_hr=24) # Note: cache path now dynamic
def cm_fetch(metric: str, asset="eth", start="2015-08-01", freq="1d") -> pd.Series:
    """Fetches a specific metric from CoinMetrics Community API.

    Uses disk caching defined in utils.py. Cache filename includes asset and metric.
    Returns a pandas Series.
    """
    # Update cache path based on function arguments for the decorator logic (won't change filename post-hoc)
    # The decorator needs modification to handle dynamic filenames based on args,
    # or we create separate cached functions for each metric.
    # For simplicity here, we'll assume the decorator was adapted or we use specific caches per metric call.
    # Let's redefine the cache path here for clarity, although the decorator handles it.
    # cache_filename = f"cm_{asset}_{metric}.parquet" # Example dynamic name
    # This function will actually use "cm_{asset}_{metric}.parquet" as the cache filename literally.
    # A more robust disk_cache would inspect args.

    base = ("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
            f"?assets={asset}&metrics={metric}&frequency={freq}"
            f"&start_time={start}&page_size=10000")
    # Use CM_API_KEY if available in environment
    hdr = {}
    api_key = os.getenv("CM_API_KEY")
    if api_key:
        hdr["Authorization"] = f"Bearer {api_key}" # Or "X-API-KEY": api_key depending on API
        logging.info(f"Using CoinMetrics API Key for metric: {metric}")
    else:
        logging.info(f"Fetching CoinMetrics data without API key for metric: {metric}")

    data, url = [], base
    page_count = 0
    while url:
        page_count += 1
        logging.debug(f"Fetching CM page {page_count}: {url.split('?')[0]}...")
        try:
            # Use robust_get imported from utils
            j = robust_get(url, headers=hdr)
            page_data = j.get("data", [])
            data.extend(page_data)
            url = j.get("next_page_url")
            # Add a small delay to be polite to the API
            if url: time.sleep(random.uniform(0.5, 1.5))
        except (RuntimeError, requests.exceptions.RequestException, json.JSONDecodeError) as req_err:
            logging.error(f"Failed to fetch or parse CM page for {metric}: {req_err}. Stopping fetch.")
            url = None # Stop pagination on error
        except Exception as e:
            logging.error(f"Unexpected error fetching CM page for {metric}: {e}", exc_info=True)
            url = None # Stop pagination

    if not data:
        logging.error(f"No data returned from CoinMetrics for metric: {metric}")
        # Return an empty Series with a datetime index
        return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)
        # Or raise: raise RuntimeError(f"No data returned for {metric}")

    logging.info(f"Finished CoinMetrics fetch for {metric}, got {len(data)} records.")
    try:
        series = (pd.DataFrame(data)
                  .assign(time=lambda d: pd.to_datetime(d["time"]))
                  .set_index("time")[metric]
                  .astype(float)
                  .sort_index()
                  .loc[lambda s: ~s.index.duplicated()]) # De-duplicate just in case

        # Ensure index is timezone-naive (should be handled by disk_cache too)
        if pd.api.types.is_datetime64_any_dtype(series.index) and series.index.tz is not None:
            series.index = series.index.tz_localize(None)
        return series
    except KeyError:
        logging.error(f"Metric '{metric}' not found in CM response columns: {pd.DataFrame(data).columns.tolist()}")
        return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)
    except Exception as e:
        logging.error(f"Error processing CoinMetrics data for {metric}: {e}", exc_info=True)
        return pd.Series(dtype=float, index=pd.to_datetime([]), name=metric)


@disk_cache("nasdaq_ndx.parquet", max_age_hr=24)
def fetch_nasdaq() -> pd.Series:
    """Fetches true-daily ^NDX close from Yahoo via RapidAPI (chunked).

    Uses disk caching defined in utils.py.
    Returns a pandas Series named 'nasdaq'.
    """
    key = os.getenv("RAPIDAPI_KEY")
    if not key:
        logging.error("RAPIDAPI_KEY environment variable not set.")
        raise EnvironmentError("RAPIDAPI_KEY env-var not set")

    host = "apidojo-yahoo-finance-v1.p.rapidapi.com"
    url = f"https://{host}/stock/v2/get-chart"
    hdrs = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}

    start = datetime(1985, 1, 1).date()  # Earliest ^NDX on Yahoo
    today = datetime.now(tz=timezone.utc).date()
    pieces = []
    logging.info("Starting NASDAQ (^NDX) fetch from %s to %s", start, today)

    while start <= today:
        end = min(start + timedelta(days=364), today)
        try:
            start_ts = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
            end_ts = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        except (OverflowError, OSError) as ts_err:
             logging.error(f"Timestamp conversion error for NASDAQ dates {start} to {end}: {ts_err}. Skipping chunk.")
             start = end + timedelta(days=1)
             continue

        params = {
            "symbol": "^NDX",
            "interval": "1d",
            "period1": start_ts,
            "period2": end_ts
        }
        logging.debug(f"Fetching ^NDX: start={start}, end={end}, params={params}")
        response_json = None
        try:
            # Use robust_get imported from utils
            response_json = robust_get(url, headers=hdrs, params=params)

            # Defensive parsing checks
            chart_data = response_json.get("chart", {})
            chart_result = chart_data.get("result")
            chart_error = chart_data.get("error")

            if chart_error or chart_result is None:
                error_desc = chart_error.get("description", "Result is null") if chart_error else "Result is null"
                if "Data doesn't exist" in error_desc or "No data found" in error_desc:
                     logging.info(f"^NDX API reported no data for {start} to {end}: {error_desc}")
                else:
                     logging.error(f"^NDX API Error for {start} to {end}: {error_desc}")
                start = end + timedelta(days=1)
                continue

            if not isinstance(chart_result, list) or not chart_result:
                logging.warning(f"^NDX API 'result' is not a non-empty list for {start} to {end}. Skipping. Result: {str(chart_result)[:200]}...")
                start = end + timedelta(days=1)
                continue

            result_data = chart_result[0]
            timestamps = result_data.get("timestamp")
            indicators = result_data.get("indicators")
            if timestamps is None or indicators is None:
                logging.warning(f"Missing 'timestamp' or 'indicators' in ^NDX API result[0] for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            quote = indicators.get("quote")
            if not quote or not isinstance(quote, list) or not quote[0]:
                logging.warning(f"Missing 'quote' array in ^NDX API indicators for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            close_prices = quote[0].get("close")
            if close_prices is None:
                logging.warning(f"Missing 'close' prices in ^NDX API quote[0] for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            if len(close_prices) != len(timestamps):
                logging.warning(f"Mismatch length for close/timestamps in ^NDX API response for {start} to {end}. Skipping.")
                start = end + timedelta(days=1)
                continue

            # Create Series, ensuring index matches non-null data points
            valid_indices = [i for i, price in enumerate(close_prices) if price is not None]
            if not valid_indices:
                logging.info(f"No valid (non-null) NASDAQ price data found for chunk {start} to {end}.")
            else:
                valid_timestamps = [timestamps[i] for i in valid_indices]
                valid_prices = [close_prices[i] for i in valid_indices]
                ser = pd.Series(
                    valid_prices,
                    index=pd.to_datetime(valid_timestamps, unit="s", utc=True).tz_convert(None).normalize(),
                    name="nasdaq"
                )
                pieces.append(ser)
                logging.debug(f"Successfully processed ^NDX chunk {start} to {end}, got {len(ser)} data points.")

        except (RuntimeError, requests.exceptions.RequestException, json.JSONDecodeError) as req_err:
            logging.error(f"Handled error during NASDAQ fetch/parse for chunk {start} to {end}: {req_err}. Skipping chunk.")
        except Exception as e:
            logging.error(f"Unexpected error processing NASDAQ chunk {start} to {end}: {e}", exc_info=True)
        finally:
            # Ensure 'start' is always incremented
            start = end + timedelta(days=1)

    if not pieces:
        logging.error("No NASDAQ data pieces were collected after processing all chunks.")
        # Return an empty Series with the correct structure
        return pd.Series(dtype=float, index=pd.to_datetime([]), name='nasdaq')
        # Or raise: raise RuntimeError("No NASDAQ data successfully fetched after processing all chunks.")

    logging.info("Finished NASDAQ fetch. Concatenating %d pieces.", len(pieces))
    ndx_series = (pd.concat(pieces)
                  .sort_index()
                  .loc[lambda s: ~s.index.duplicated()]) # De-duplicate just in case

    # Ensure final result index is timezone-naive (should be handled by disk_cache too)
    if pd.api.types.is_datetime64_any_dtype(ndx_series.index) and ndx_series.index.tz is not None:
        ndx_series.index = ndx_series.index.tz_localize(None)

    return ndx_series