# src/utils/cache.py

import inspect  # Import inspect module
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict  # Import Dict

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


def disk_cache(
    path_arg_template: str, max_age_hr: int = 24
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to cache pandas DataFrame/Series to disk (Parquet).

    Supports dynamic path formatting based on function arguments.
    Example: @disk_cache("item_{arg1}_{kwarg2}.parquet")
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Get function signature to map args/kwargs to names for formatting
        sig = inspect.signature(func)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # --- Determine dynamic cache path INSIDE wrapper ---
            try:
                # Bind passed args/kwargs to function signature parameter names
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                # Create a dictionary of all arguments for formatting
                format_dict: Dict[str, Any] = bound_args.arguments
                # Format the path template using the arguments
                cache_filename = path_arg_template.format(**format_dict)
            except (TypeError, ValueError, KeyError) as fmt_err:
                # Fallback or error if formatting fails
                logging.error(
                    f"Failed to format cache path template '{path_arg_template}' "
                    f"for {func.__name__} with args={args}, kwargs={kwargs}: {fmt_err}. "
                    "Caching disabled for this call."
                )
                # Execute function without caching if path formatting fails
                return func(*args, **kwargs)

            cache_path = settings.DATA_DIR / cache_filename
            lock_path = cache_path.with_suffix(".lock")
            meta_path = cache_path.with_suffix(".meta.json")
            # --- End dynamic path determination ---

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
                result = func(*args, **kwargs)  # Call original function

                # --- Cache the result ---
                tmp_path = cache_path.with_suffix(".tmp")

                # Determine result type *before* potential modification
                is_series = isinstance(result, pd.Series)
                is_dataframe = isinstance(result, pd.DataFrame)

                # Ensure data index is timezone-naive BEFORE saving
                if (
                    hasattr(result, "index")
                    and pd.api.types.is_datetime64_any_dtype(result.index)
                    and result.index.tz is not None
                ):
                    result_to_save = result.copy()
                    result_to_save.index = result_to_save.index.tz_localize(None)
                else:
                    # Use result directly if no tz conversion needed or if not Series/DataFrame
                    result_to_save = result

                # Only attempt to save if it's a Series or DataFrame
                if is_series or is_dataframe:
                    try:
                        # Save result to temporary file
                        if is_series:
                            # Ensure the Series has a name before converting to frame
                            if result_to_save.name is None:
                                # Try to infer name from formatting dict if possible, else use default
                                series_name = format_dict.get(
                                    "metric", "value"
                                )  # Example fallback
                                result_to_save.name = str(series_name)

                            result_to_save.to_frame().to_parquet(tmp_path, index=True)
                        else:  # is_dataframe
                            result_to_save.to_parquet(tmp_path, index=True)

                        # Move temporary file to final cache path
                        shutil.move(
                            str(tmp_path), str(cache_path)
                        )  # Ensure paths are strings for shutil
                        logging.info(f"Saved fresh data to cache: {cache_path.name}")

                        # Write sibling metadata file
                        try:
                            meta = {
                                "pandas_type": "Series" if is_series else "DataFrame",
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            }
                            with open(meta_path, "w") as f:
                                json.dump(meta, f, indent=4)
                            logging.debug(f"Wrote cache metadata to: {meta_path.name}")
                        except Exception as meta_e:
                            logging.error(
                                f"Failed to write cache metadata for {cache_path}: {meta_e}"
                            )

                    except Exception as e:
                        logging.error(f"Failed to save cache file {cache_path}: {e}")
                        if tmp_path.exists():
                            try:
                                tmp_path.unlink()
                            except OSError as unlink_e:
                                logging.error(
                                    f"Failed to remove temporary cache file {tmp_path}: {unlink_e}"
                                )
                else:
                    # Log if trying to cache unsupported type, but still return original result
                    logging.warning(
                        f"Cannot cache result of type {type(result)} from {func.__name__}. "
                        "Returning uncached result."
                    )
                # --- End Caching ---

            # Return the original result
            return result

        return wrapper

    return decorator
