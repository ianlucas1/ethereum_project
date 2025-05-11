# src/utils/file_io.py

import logging
from pathlib import Path

import pandas as pd


def load_parquet(path: Path, req_cols: list[str] | None = None) -> pd.DataFrame:
    """Loads parquet, ensures 'time' index, checks columns."""
    if not path.exists():
        logging.error(f"Parquet file not found: {path}")
        raise FileNotFoundError(path)
    try:
        df = pd.read_parquet(path)
        # Ensure 'time' column exists before setting index
        if "time" not in df.columns:
            if df.index.name == "time":
                df = df.reset_index()  # Reset if 'time' is already the index name
            else:
                # Fallback: If index has no name or different name, reset and rename first col
                logging.warning(
                    f"Parquet {path.name} missing 'time' column, using index or first column."
                )
                # Try using index if it's datetime-like, otherwise use first column
                if pd.api.types.is_datetime64_any_dtype(df.index):
                    col_name = df.index.name or "index_col"  # Use index name or default
                    df = df.reset_index().rename(columns={col_name: "time"})
                elif len(df.columns) > 0:
                    # If index isn't datetime, try resetting and using the first column if it exists
                    df.columns.tolist()
                    df = df.reset_index(drop=True)  # Drop the non-datetime index
                    # Check if first column looks like time after reset
                    if pd.api.types.is_datetime64_any_dtype(df.iloc[:, 0]):
                        df = df.rename(columns={df.columns[0]: "time"})
                    else:
                        # If first column isn't time either, raise error
                        raise ValueError(
                            f"Parquet {path.name} missing 'time' column and index/first column not suitable."
                        )
                else:
                    raise ValueError(
                        f"Parquet {path.name} missing 'time' column and has no other columns."
                    )

        # Convert to datetime, set index, sort, ensure timezone-naive
        df = (
            df.assign(time=lambda d: pd.to_datetime(d["time"]))
            .set_index("time")
            .sort_index()
        )
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        if req_cols:
            missing_cols = [c for c in req_cols if c not in df.columns]
            if missing_cols:
                raise ValueError(
                    f"{path.name} missing required columns: {missing_cols}"
                )
        return df
    except Exception as e:
        logging.error(
            f"Failed to load or process parquet file {path}: {e}", exc_info=True
        )
        raise  # Re-raise the exception after logging
