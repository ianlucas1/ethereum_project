"""
Exploratory-data-analysis helpers
───────────────────────────────────────────────────────────────────────────────
* winsorise outliers (optionally inside a window)
* run ADF / KPSS stationarity tests
* quick demo:  python -m src.eda
"""

from __future__ import annotations

import logging
from typing import (
    Any,
    Callable,
    Iterable,
    Sequence,
    TYPE_CHECKING,
    cast,
)  # Added Callable

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Winsorisation                                                               #
# --------------------------------------------------------------------------- #


def _normalise_mask(
    df: pd.DataFrame,
    window_mask: Sequence[bool] | pd.Index | None,
) -> pd.Series:
    """Normalises various mask types into a boolean Series aligned to df.index.

    Handles None (select all), boolean sequences, or index labels.

    Args:
        df (pd.DataFrame): The DataFrame whose index the mask should align with.
        window_mask (Sequence[bool] | pd.Index | None): The mask input.
            - If None, returns a Series of True.
            - If a boolean sequence of the same length as df, uses it directly.
            - Otherwise, treats it as a collection of index labels to select.

    Returns:
        pd.Series: A boolean Series indicating selected rows, aligned to df.index.
    """
    if window_mask is None:
        return pd.Series(True, index=df.index, name="mask")

    # Check if it's a sequence of booleans matching df length
    if isinstance(window_mask, (pd.Series, np.ndarray, list, tuple)) and len(
        window_mask
    ) == len(df):
        # Ensure boolean type
        return pd.Series(window_mask, index=df.index, name="mask").astype(bool)

    # Treat as an index-label collection (works for pd.Index, list of labels, etc.)
    # Ensure the resulting Series is boolean
    return pd.Series(df.index.isin(window_mask), index=df.index, name="mask").astype(
        bool
    )


def winsorize_data(
    *,
    df: pd.DataFrame,
    cols_to_cap: list[str],
    quantile: float,
    window_mask: Sequence[bool] | pd.Index | None = None,
) -> pd.DataFrame:
    """Caps the upper tail of specified columns at a given quantile.

    Calculates the quantile threshold based only on the rows selected by
    `window_mask` (if provided) to prevent lookahead bias. Then, caps values
    in `cols_to_cap` that exceed this threshold, but only within the rows
    selected by `window_mask`.

    Args:
        df (pd.DataFrame): The input DataFrame.
        cols_to_cap (list[str]): List of column names to apply winsorization to.
        quantile (float): The upper quantile (e.g., 0.99) to cap at.
        window_mask (Sequence[bool] | pd.Index | None, optional):
            A mask indicating the subset of rows used to calculate the quantile
            threshold and apply the capping. If None, uses the entire DataFrame.
            Defaults to None.

    Returns:
        pd.DataFrame: A copy of the input DataFrame with specified columns capped.
    """
    df_out = df.copy()
    mask = _normalise_mask(df_out, window_mask)

    # Calculate caps based *only* on the masked window
    caps = df_out.loc[mask, cols_to_cap].quantile(quantile)
    for col, cap_val in caps.items():
        # Apply capping *only* within the masked window
        mask_to_cap = (df_out[col] > cap_val) & mask
        if pd.api.types.is_integer_dtype(df_out[col]) and isinstance(cap_val, float):
            df_out[col] = df_out[col].astype(float)
        df_out.loc[mask_to_cap, col] = cap_val

    return df_out


# --------------------------------------------------------------------------- #
# Stationarity tests                                                          #
# --------------------------------------------------------------------------- #


def _adf(series: pd.Series) -> float:
    """Calculates the Augmented Dickey-Fuller test p-value.

    Args:
        series (pd.Series): The time series data to test. NaNs are dropped.

    Returns:
        float: The ADF test p-value.
    """
    # adfuller returns tuple: (adf_stat, p_value, used_lag, n_obs, critical_values, ic_best)
    result: tuple[float, float, int, int, dict[str, float], float | None] = adfuller(
        series.dropna()
    )
    return cast(float, result[1])  # Return p-value


def _kpss(series: pd.Series) -> float:
    """Calculates the KPSS test p-value (null hypothesis: stationarity).

    Uses 'auto' method for lag selection. Suppresses invalid value warnings
    that can occur during the test.

    Args:
        series (pd.Series): The time series data to test. NaNs are dropped.

    Returns:
        float: The KPSS test p-value.
    """
    with np.errstate(invalid="ignore"):
        # kpss returns tuple: (kpss_stat, p_value, lags, critical_values)
        result: tuple[float, float, int, dict[str, float]] = kpss(
            series.dropna(), nlags="auto"
        )
        return cast(float, result[1])  # Return p-value


def run_stationarity_tests(
    *,
    df: pd.DataFrame,
    cols_to_test: Iterable[str],
    window_mask: Sequence[bool] | pd.Index | None = None,
) -> pd.DataFrame:
    """Runs ADF and KPSS stationarity tests on specified columns within a window.

    Applies the tests only to the subset of data selected by `window_mask`.

    Args:
        df (pd.DataFrame): The input DataFrame containing time series data.
        cols_to_test (Iterable[str]): Sequence of column names to test.
        window_mask (Sequence[bool] | pd.Index | None, optional):
            A mask indicating the subset of rows to perform the tests on.
            If None, uses the entire DataFrame. Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame with columns 'series', 'ADF p', 'KPSS p',
                      summarizing the test results for each column.
    """
    mask = _normalise_mask(df, window_mask)
    rows: list[dict[str, Any]] = []  # Initialize list for results
    for col in cols_to_test:
        series_to_test = df.loc[mask, col]
        if series_to_test.dropna().empty:
            logger.warning(
                f"Skipping stationarity tests for '{col}': No non-NaN data in window."
            )
            adf_p = np.nan
            kpss_p = np.nan
        else:
            adf_p = _adf(series_to_test)
            kpss_p = _kpss(series_to_test)

        rows.append(
            {
                "series": col,
                "ADF p": adf_p,
                "KPSS p": kpss_p,
            }
        )
    return pd.DataFrame(rows, columns=["series", "ADF p", "KPSS p"])


# --------------------------------------------------------------------------- #
# Safe display helper (works inside head-less CI too)                         #
# --------------------------------------------------------------------------- #

if TYPE_CHECKING:  # for static analysers
    # Define display type for type checkers
    display: Callable[[Any], None]

try:
    # Try importing the IPython display function
    from IPython.display import display as display  # type: ignore[no-redef] # Allow redefinition
except ModuleNotFoundError:  # pragma: no cover
    # Fallback function if IPython is not available
    def display(obj: Any) -> None:  # noqa: F811 # Allow redefinition for linters
        """Fallback plain print when IPython is unavailable.

        Args:
            obj (Any): The object to print.
        """
        print(obj)


# --------------------------------------------------------------------------- #
# CLI demo                                                                    #
# --------------------------------------------------------------------------- #


def _demo() -> pd.DataFrame:
    """Runs a mini demo showing winsorisation + stationarity helpers.

    Generates sample data, applies winsorization to the last 2 years of
    'volume', runs stationarity tests on the winsorized data for the same
    window, and prints the results.

    Returns:
        pd.DataFrame: The DataFrame containing stationarity test results.
    """
    logging.basicConfig(level=logging.INFO)

    rng = pd.date_range("2018-01-01", periods=120, freq="M")
    df = pd.DataFrame(
        {
            "price": np.random.lognormal(mean=0.1, sigma=0.2, size=len(rng)).cumsum(),
            "volume": np.random.chisquare(df=8.0, size=len(rng)),
        },
        index=rng,
    )

    df_w = winsorize_data(
        df=df,
        cols_to_cap=["volume"],
        quantile=0.95,
        window_mask=df.index[-24:],  # last two years
    )

    tbl = run_stationarity_tests(
        df=df_w,
        cols_to_test=["price", "volume"],
        window_mask=df.index[-24:],
    )

    print("\n--- Stationarity Test Results ---")
    display(tbl)  # Use the potentially redefined display function
    print("---------------------------------\n")
    return tbl


if __name__ == "__main__":
    _demo()
