# src/utils/cache.py

import logging
import json
import shutil
from datetime import datetime, timedelta, timezone
from typing import Callable, Any
import pandas as pd

# Import settings from config relative to the src directory
from src.config import settings

# Safe import for filelock - raise error if missing
try:
    from filelock import FileLock
except ModuleNotFoundError as e:
    raise ImportError(
        "'filelock' is missing. Activate your venv and run "
        "'pip install -r requirements-lock.txt'"
    ) from e


def disk_cache(path_arg: str, max_age_hr: int = 24) -> Callable:
    """Decorator to cache pandas DataFrame/Series to disk (Parquet)."""
    # Note: cache_path and lock_path are now defined inside the wrapper

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs) -> Any:
            # --- MOVED INSIDE WRAPPER ---
            # Construct paths using the potentially patched settings.DATA_DIR
            cache_path = settings.DATA_DIR / path_arg
            lock_path = cache_path.with_suffix(".lock")
            # --- END OF MOVE ---

            # Check cache existence and age
            if cache_path.exists():
                try:
                    cache_mtime_ts = cache_path.stat().st_mtime
                    cache_mtime = datetime.fromtimestamp(
                        cache_mtime_ts, tz=timezone.utc
                    )
                    now = datetime.now(tz=timezone.utc)
                    age = now - cache_mtime
                    if age < timedelta(hours=max_age_hr):
                        logging.info(f"Loading cached result from: {cache_path.name}")

                        # --- 3.3.2: read metadata to choose pandas type ---
                        meta_path = cache_path.with_suffix(".meta.json")
                        pandas_type: str | None = None
                        if meta_path.exists():
                            try:
                                with open(meta_path) as f:
                                    meta = json.load(f)
                                pandas_type = meta.get("pandas_type")
                            except (json.JSONDecodeError, OSError) as meta_e:
                                logging.warning(
                                    f"Could not read cache metadata for {cache_path.name}: {meta_e}"
                                )
                        # -------------------------------------------------

                        # Fallback: default to DataFrame, but convert to Series
                        # when there's exactly one column (common for Series saved
                        # via `to_parquet`) and no explicit meta.
                        df = pd.read_parquet(cache_path)
                        if pandas_type == "Series" or (
                            pandas_type is None and df.shape[1] == 1
                        ):
                            return df.iloc[:, 0]
                        return df
                except Exception as e:
                    logging.warning(
                        f"Failed to load or check cache {cache_path}: {e}. Re-fetching."
                    )

            # Execute function, acquire lock, save result
            with FileLock(lock_path):
                logging.info(
                    f"Cache miss or expired for {cache_path.name}. Calling function {func.__name__}."
                )
                result = func(*args, **kwargs)
                tmp_path = cache_path.with_suffix(".tmp")

                # Ensure data index is timezone-naive BEFORE saving
                if (
                    hasattr(result, "index")
                    and pd.api.types.is_datetime64_any_dtype(result.index)
                    and result.index.tz is not None
                ):
                    # Create a copy to avoid modifying the original result if it's used elsewhere
                    result_to_save = result.copy()
                    result_to_save.index = result_to_save.index.tz_localize(None)
                else:
                    result_to_save = result  # No modification needed

                try:
                    # Save result to temporary file
                    if isinstance(result_to_save, pd.Series):
                        result_to_save.to_frame().to_parquet(
                            tmp_path, index=True
                        )  # Save Series as one-column DataFrame
                    elif isinstance(result_to_save, pd.DataFrame):
                        result_to_save.to_parquet(tmp_path, index=True)
                    else:
                        logging.error(
                            f"Cannot cache result of type {type(result_to_save)} from {func.__name__}."
                        )
                        return result  # Return uncached result if not DataFrame/Series

                    # Move temporary file to final cache path
                    shutil.move(tmp_path, cache_path)
                    logging.info(f"Saved fresh data to cache: {cache_path.name}")

                    # --- 3.3.1: write sibling metadata file ---
                    try:
                        meta = {
                            "pandas_type": "Series"
                            if isinstance(result_to_save, pd.Series)
                            else "DataFrame",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                        meta_path = cache_path.with_suffix(".meta.json")
                        with open(meta_path, "w") as f:
                            json.dump(meta, f, indent=4)
                        logging.debug(f"Wrote cache metadata to: {meta_path.name}")
                    except Exception as meta_e:
                        logging.error(
                            f"Failed to write cache metadata for {cache_path}: {meta_e}"
                        )
                    # --- end 3.3.1 ---

                except Exception as e:
                    logging.error(f"Failed to save cache file {cache_path}: {e}")
                    # Clean up temp file if it exists
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except OSError as unlink_e:
                            logging.error(
                                f"Failed to remove temporary cache file {tmp_path}: {unlink_e}"
                            )
            # Return the original result (potentially with tz-aware index if it started that way)
            return result

        return wrapper

    return decorator
