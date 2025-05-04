import pandas as pd
import pytest
from pathlib import Path

from src.utils.file_io import load_parquet


def test_load_parquet_happy_path(tmp_path: Path):
    """Test loading a valid parquet file with a 'time' column."""
    file_path = tmp_path / "test.parquet"
    original_data = {
        "time": pd.to_datetime(["2023-01-01 10:00:00", "2023-01-01 11:00:00"]),
        "value1": [1, 2],
        "value2": [3.0, 4.0],
    }
    original_df = pd.DataFrame(original_data)

    # Save to parquet
    original_df.to_parquet(file_path)

    # Load using the function
    loaded_df = load_parquet(file_path, req_cols=["value1", "value2"])

    # Prepare expected DataFrame (with 'time' as DatetimeIndex)
    expected_df = original_df.set_index("time")

    # Assertions
    pd.testing.assert_frame_equal(loaded_df, expected_df)
    assert isinstance(loaded_df.index, pd.DatetimeIndex)
    assert loaded_df.index.tz is None  # Ensure timezone naive


def test_load_parquet_missing_file(tmp_path: Path):
    """Test loading a non-existent parquet file raises FileNotFoundError."""
    non_existent_path = tmp_path / "non_existent.parquet"
    with pytest.raises(FileNotFoundError):
        load_parquet(non_existent_path)


def test_load_parquet_missing_required_column(tmp_path: Path):
    """Test loading a parquet file missing a required column raises ValueError."""
    file_path = tmp_path / "test_missing_col.parquet"
    data_missing_col = {
        "time": pd.to_datetime(["2023-01-01 10:00:00", "2023-01-01 11:00:00"]),
        "value1": [1, 2],
        # 'value2' is missing
    }
    df_missing_col = pd.DataFrame(data_missing_col)

    # Save to parquet
    df_missing_col.to_parquet(file_path)

    # Load and require 'value2'
    # Capture the exception instead of using regex match
    with pytest.raises(ValueError) as excinfo:
        load_parquet(file_path, req_cols=["value1", "value2"])

    # Assert the exact error message string
    expected_msg = f"{file_path.name} missing required columns: ['value2']"
    assert str(excinfo.value) == expected_msg
