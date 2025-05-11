# tests/test_eda.py

import pandas as pd
import pytest

# Assuming src is importable via conftest.py
from src.eda import winsorize_data  # Add stationarity later if needed

# --- Fixtures ---


@pytest.fixture
def sample_eda_data() -> pd.DataFrame:
    """Provides sample data for EDA function tests."""
    dates = pd.to_datetime(
        [
            "2023-01-01",
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
            "2023-01-06",
        ]
    )
    df = pd.DataFrame(
        {
            "value1": [10, 12, 11, 13, 100, 15],  # Outlier at index 4
            "value2": [20, 22, 21, 23, 24, 200],  # Outlier at index 5
            "value3": [5, 6, 7, 8, 9, 10],  # No outliers relative to 90th percentile
        },
        index=dates,
    )
    return df


# --- Tests for winsorize_data ---


def test_winsorize_data_no_mask(sample_eda_data: pd.DataFrame):
    """Tests winsorizing entire DataFrame."""
    df_input = sample_eda_data
    cols_to_cap = ["value1", "value2"]
    quantile = 0.90

    df_output = winsorize_data(df=df_input, cols_to_cap=cols_to_cap, quantile=quantile)

    # Calculate expected caps based on full data
    # value1: [10, 11, 12, 13, 15, 100] -> 90th percentile is around 43.5 (interp) or 15 (nearest)
    # Let's use pandas quantile for consistency
    cap1 = df_input["value1"].quantile(quantile)  # Should cap 100
    cap2 = df_input["value2"].quantile(quantile)  # Should cap 200

    # Check that outliers were capped
    assert df_output.loc["2023-01-05", "value1"] == cap1
    assert df_output.loc["2023-01-06", "value2"] == cap2

    # Check that other values were not capped (or capped correctly if they exceeded)
    assert (
        df_output.loc["2023-01-04", "value1"] == df_input.loc["2023-01-04", "value1"]
    )  # 13 < cap1
    assert (
        df_output.loc["2023-01-05", "value2"] == df_input.loc["2023-01-05", "value2"]
    )  # 24 < cap2

    # Check that uncapped column remains unchanged
    pd.testing.assert_series_equal(df_output["value3"], df_input["value3"])

    # Check original df is not modified
    assert df_input.loc["2023-01-05", "value1"] == 100
    assert df_input.loc["2023-01-06", "value2"] == 200


def test_winsorize_data_with_mask(sample_eda_data: pd.DataFrame):
    """Tests winsorizing only within a specified window mask."""
    df_input = sample_eda_data
    cols_to_cap = ["value1", "value2"]
    quantile = 0.90
    # Mask selects first 4 rows (excluding outliers)
    mask = df_input.index < "2023-01-05"

    df_output = winsorize_data(
        df=df_input, cols_to_cap=cols_to_cap, quantile=quantile, window_mask=mask
    )

    # Calculate expected caps based ONLY on the masked window
    cap1_masked = df_input.loc[mask, "value1"].quantile(
        quantile
    )  # 90th of [10,12,11,13] -> 12.7
    cap2_masked = df_input.loc[mask, "value2"].quantile(
        quantile
    )  # 90th of [20,22,21,23] -> 22.7

    # Check that values *within* the mask were capped correctly
    assert df_output.loc["2023-01-04", "value1"] == cap1_masked  # 13 capped to 12.7
    assert df_output.loc["2023-01-04", "value2"] == cap2_masked  # 23 capped to 22.7
    assert (
        df_output.loc["2023-01-02", "value1"] == df_input.loc["2023-01-02", "value1"]
    )  # 12 not capped

    # Check that values *outside* the mask were NOT capped
    assert df_output.loc["2023-01-05", "value1"] == 100  # Outlier untouched
    assert df_output.loc["2023-01-06", "value2"] == 200  # Outlier untouched

    # Check that uncapped column remains unchanged
    pd.testing.assert_series_equal(df_output["value3"], df_input["value3"])
