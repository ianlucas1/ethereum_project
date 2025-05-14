#!/usr/bin/env python
"""
Single-source-of-truth Road-map synchroniser.

• Reads prompts/roadmap.jsonl
• If any task is IN PROGRESS → that's the active ticket.
• Else finds the first NOT STARTED task (skipping Section headers)
  → sets need_rollover=True
• If rollover required: rewrites roadmap.jsonl (set completedID->DONE,
  nextID->IN PROGRESS) and rewrites §5 Current ticket in prompts/starter_prompt.txt
Outputs JSON summary for the coding agent to consume.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"
ROADMAP = PROMPTS / "roadmap.jsonl"
STARTER = PROMPTS / "starter_prompt.txt"


def load_roadmap():
    return [
        json.loads(line) for line in ROADMAP.read_text().splitlines() if line.strip()
    ]


def find_active(tasks):
    inprog = [t for t in tasks if t["Status"] == "IN PROGRESS"]
    if inprog:
        return inprog[0], False
    # first actionable NOT STARTED (skip Type==Section)
    for t in tasks:
        if t["Status"] == "NOT STARTED" and t["Type"] != "Section":
            return t, True
    raise RuntimeError("No actionable task found")


def rewrite_files(completed_id: str | None, next_task: dict):
    today = datetime.date.today().isoformat()
    lines = []
    for t in load_roadmap():
        if completed_id and t["ID"] == completed_id:
            t["Status"], t["Completion_Date"] = "DONE", today
        if t["ID"] == next_task["ID"]:
            t["Status"] = "IN PROGRESS"
            if t["Start_Date"] in ("N/A", ""):
                t["Start_Date"] = today
        lines.append(json.dumps(t))
    ROADMAP.write_text("\n".join(lines))

    # update starter_prompt.txt §5 block
    txt = STARTER.read_text()
    new_block = (
        f"## ❸ Current ticket  (SYNC {next_task['ID']})\n\n"
        f"> *This block is rewritten automatically by `scripts/roadmap_sync.py`.*\n\n"
        f"**Ticket ID:** `{next_task['ID']}` — *{next_task['Task_Title']}*\n"
        f"**Branch:** `feature/{next_task['ID']}-"
        f"{re.sub(r'[^a-z0-9-]+', '-', next_task['Task_Title'].lower())[:20].strip('-')}`"
        f"`\n\n"
        f"### Tasks\n• TBD by agent\n"
    )
    STARTER.write_text(re.sub(r"## ❸[\s\S]*", new_block, txt))


def main():
    tasks = load_roadmap()
    active, need_rollover = find_active(tasks)
    if need_rollover:
        # assume previous ticket is last DONE before this index
        idx = tasks.index(active)
        completed = next((t for t in tasks[:idx][::-1] if t["Status"] == "DONE"), None)
        rewrite_files(completed["ID"] if completed else None, active)
    summary = {
        "active_ticket": active["ID"],
        "branch_slug": re.sub(r"[^a-z0-9-]+", "-", active["Task_Title"].lower())[
            :20
        ].strip("-"),
        "need_rollover": need_rollover,
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
