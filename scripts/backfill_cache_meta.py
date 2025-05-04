#!/usr/bin/env python
"""
Back-fill `.meta.json` files for existing Parquet caches.

Usage
-----
python scripts/backfill_cache_meta.py <cache_directory> [--overwrite]

If <cache_directory> is omitted, the script defaults to
`settings.DATA_DIR` (the same root used by `disk_cache`).

The script walks the directory tree recursively, ensuring that every
`*.parquet` file has a sibling `*.meta.json`.  The metadata contains:

    {
        "pandas_type": "Series" | "DataFrame",
        "created_at": "<ISO-8601 UTC timestamp>"
    }
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    # Optional import – only present inside project
    from settings import DATA_DIR  # type: ignore
except ImportError:  # Fallback when running outside project root
    DATA_DIR = Path.cwd()

logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)


def parquet_files(root: Path) -> Iterable[Path]:
    """Yield all `.parquet` files under *root* (recursively)."""
    yield from root.rglob("*.parquet")


def write_meta(pq_path: Path, overwrite: bool = False) -> None:
    """Create or update the metadata file adjacent to *pq_path*."""
    meta_path = pq_path.with_suffix(".meta.json")
    if meta_path.exists() and not overwrite:
        logging.debug("Meta exists, skipping: %s", meta_path)
        return

    # Load just enough to infer pandas type
    obj = pd.read_parquet(pq_path)
    pandas_type = "Series" if isinstance(obj, pd.Series) else "DataFrame"

    meta = {
        "pandas_type": pandas_type,
        # Use file mtime as best proxy for creation when back-filling
        "created_at": datetime.fromtimestamp(
            pq_path.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
    }

    with open(meta_path, "w") as fp:
        json.dump(meta, fp, indent=4)

    logging.info("Wrote meta for %s", pq_path.relative_to(pq_path.parent.parent))


def backfill(directory: Path, overwrite: bool = False) -> None:
    """Back-fill metadata for every parquet file under *directory*."""
    for pq in parquet_files(directory):
        try:
            write_meta(pq, overwrite=overwrite)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed on %s: %s", pq, exc)


def parse_args() -> argparse.Namespace:  # noqa: D401
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Back-fill .meta.json files for cached Parquet files."
    )
    parser.add_argument(
        "cache_directory",
        nargs="?",
        default=DATA_DIR,
        type=Path,
        help=f"Root directory containing cache parquet files (default: {DATA_DIR})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .meta.json files.",
    )
    return parser.parse_args()


def main() -> None:  # noqa: D401
    """CLI entry-point."""
    args = parse_args()
    backfill(args.cache_directory, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
