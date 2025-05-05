"""
Exploratory-data-analysis helpers
───────────────────────────────────────────────────────────────────────────────
* winsorise outliers (optionally inside a window)
* run ADF / KPSS stationarity tests
* quick demo:  python -m src.eda
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence, TYPE_CHECKING, cast

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
    """Return a boolean Series aligned to *df.index* selecting the rows of interest."""
    if window_mask is None:
        return pd.Series(True, index=df.index, name="mask")

    if isinstance(window_mask, (pd.Series, np.ndarray, list, tuple)) and len(
        window_mask
    ) == len(df):
        return pd.Series(window_mask, index=df.index, name="mask").astype(bool)

    # treat as an index-label collection
    return pd.Series(df.index.isin(window_mask), index=df.index, name="mask")


def winsorize_data(
    *,
    df: pd.DataFrame,
    cols_to_cap: list[str],
    quantile: float,
    window_mask: Sequence[bool] | pd.Index | None = None,
) -> pd.DataFrame:
    """Cap the upper tail of *cols_to_cap* within rows selected by *window_mask*."""
    df_out = df.copy()
    mask = _normalise_mask(df_out, window_mask)

    caps = df_out.loc[mask, cols_to_cap].quantile(quantile)
    for col, cap_val in caps.items():
        mask_to_cap = (df_out[col] > cap_val) & mask
        df_out.loc[mask_to_cap, col] = cap_val

    return df_out


# --------------------------------------------------------------------------- #
# Stationarity tests                                                          #
# --------------------------------------------------------------------------- #


def _adf(series: pd.Series) -> float:
    """Augmented-Dickey–Fuller p-value."""
    return cast(float, adfuller(series.dropna())[1])


def _kpss(series: pd.Series) -> float:
    """KPSS p-value (nlags='auto')."""
    with np.errstate(invalid="ignore"):
        return cast(float, kpss(series.dropna(), nlags="auto")[1])


def run_stationarity_tests(
    *,
    df: pd.DataFrame,
    cols_to_test: Iterable[str],
    window_mask: Sequence[bool] | pd.Index | None = None,
) -> pd.DataFrame:
    """Return a DataFrame with columns **series | ADF p | KPSS p**."""
    mask = _normalise_mask(df, window_mask)
    rows = [
        {
            "series": col,
            "ADF p": _adf(df.loc[mask, col]),
            "KPSS p": _kpss(df.loc[mask, col]),
        }
        for col in cols_to_test
    ]
    return pd.DataFrame(rows, columns=["series", "ADF p", "KPSS p"])


# --------------------------------------------------------------------------- #
# Safe display helper (works inside head-less CI too)                         #
# --------------------------------------------------------------------------- #

if TYPE_CHECKING:  # for static analysers
    from typing import Callable

    display: Callable[[Any], None]  # noqa: D401

try:
    from IPython.display import display as display  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover

    def display(obj: Any) -> None:  # noqa: D401
        """Fallback plain print when IPython is unavailable."""
        print(obj)


# --------------------------------------------------------------------------- #
# CLI demo                                                                    #
# --------------------------------------------------------------------------- #


def _demo() -> pd.DataFrame:
    """Mini demo showing winsorisation + stationarity helpers."""
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
    display(tbl)
    print("---------------------------------\n")
    return tbl


if __name__ == "__main__":
    _demo()
