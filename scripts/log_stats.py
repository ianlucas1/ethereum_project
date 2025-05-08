#!/usr/bin/env python
"""
Quick trend printer for quality_scoreboard.md
"""

import pathlib

md = pathlib.Path("prompts/quality_scoreboard.md").read_text().splitlines()
rows = [line for line in md if line.startswith("| 20")]
print(
    f"Rows: {len(rows)}  Mean scores:",
    [float(line.split("|")[3]) for line in rows[-5:]],
)
