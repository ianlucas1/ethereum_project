# tests/test_winsor_leak.py

import pandas as pd
import numpy as np

# Assuming src is importable due to conftest.py or PYTHONPATH setup
from src.eda import winsorize_data


def test_winsorize_leakage_prevention():
    """
    Tests that winsorizing with a window_mask only uses data within
    that window to calculate the quantile cap, preventing future leakage.
    """
    # 1. Create toy data with an obvious outlier in the 'future'
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
    # Normal values in the past, huge outlier in the future
    data = {"value": [10, 12, 11, 13, 1000, 15]}
    df = pd.DataFrame(data, index=dates)
    original_future_value = df.loc["2023-01-05", "value"]  # Store the outlier value

    # 2. Define the 'past' window mask (excluding the outlier date)
    past_window_mask = df.index < "2023-01-05"
    cols_to_cap = ["value"]
    quantile_to_cap = (
        0.90  # Set quantile low enough to cap something in the past window
    )

    # 3. Call winsorize_data using only the past window for quantile calculation
    df_winsorized = winsorize_data(
        df=df.copy(),  # Pass a copy to avoid modifying original df if reused
        cols_to_cap=cols_to_cap,
        quantile=quantile_to_cap,
        window_mask=past_window_mask,  # CRITICAL: use only past data for cap calc
    )

    # 4. Assertions
    # a) The future outlier should NOT have been changed
    assert df_winsorized.loc["2023-01-05", "value"] == original_future_value, (
        "Future outlier value was incorrectly modified by winsorizing based on past window."
    )

    # b) Check that capping *did* happen based on the past window's quantile
    #    The cap value should be the 90th percentile of [10, 12, 11, 13] = 12.8
    expected_cap_value = np.percentile([10, 12, 11, 13], 90)
    # Find the max value in the past window in the *winsorized* data
    max_past_winsorized_value = df_winsorized.loc[past_window_mask, "value"].max()
    assert max_past_winsorized_value <= expected_cap_value, (
        f"Value in past window ({max_past_winsorized_value}) exceeds expected cap value ({expected_cap_value}) based on past data."
    )

    # c) Verify a specific past value *was* capped (e.g., the 13)
    assert df_winsorized.loc["2023-01-04", "value"] == expected_cap_value, (
        "Expected past value (13) was not capped to the calculated threshold."
    )
