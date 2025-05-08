#!/usr/bin/env python
"""
Fast Δ-Assessment / Baseline audit helper
Usage:
    python scripts/qa_audit.py --mode=delta   # default
    python scripts/qa_audit.py --mode=full    # forced full scan
Stores results in prompts/quality_scoreboard.*
Keeps a cache of last_audit_sha in .qa_audit_cache
"""

from __future__ import annotations
import argparse
import json
import subprocess
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"
SCORE_MD = PROMPTS / "quality_scoreboard.md"
SCORE_JSON = ROOT / "quality_scoreboard.json"
CACHE = ROOT / ".qa_audit_cache"

AXES = [
    "Clarity & Readability",
    "Documentation Quality",
    "Coding-Style Consistency",
    "Complexity Management",
    "Modularity & Cohesion",
    "Test Coverage & Quality",
    "Performance & Efficiency",
    "Error Handling & Resilience",
    "Dependency & Security Hygiene",
    "Scalability & Extensibility",
    "Version-Control Practices",
    "Overall Maintainability",
]


def shell(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def git_changed_files(since_sha: str) -> list[str]:
    diff = shell(f"git diff --name-only {since_sha} HEAD")
    return [f for f in diff.splitlines() if f.endswith(".py")]


def ruff_lint(files: list[str]) -> int:
    if not files:
        return 0
    try:
        shell(f"ruff check {' '.join(files)}")
        return 0
    except subprocess.CalledProcessError:
        return 10  # simple penalty


def mypy_check(files: list[str]) -> int:
    if not files:
        return 0
    try:
        shell(f"mypy --strict {' '.join(files)}")
        return 0
    except subprocess.CalledProcessError:
        return 10


def radon_complexity(files: list[str]) -> int:
    if not files:
        return 0
    try:
        out = shell(f"radon cc -s {' '.join(files)}")
        worst = max((line.split()[-1] for line in out.splitlines()), default="A")
        penalty = (ord(worst) - ord("A")) * 5
        return penalty
    except subprocess.CalledProcessError:
        return 5


def run_tests(changed: list[str]) -> float:
    target = " ".join(changed) if changed else "src"
    shell(f"pytest --cov={target} -q")
    cov_xml = ROOT / "coverage.xml"
    if cov_xml.exists():
        txt = cov_xml.read_text()
        try:
            cov = float(txt.split('line-rate="')[1].split('"')[0]) * 100
        except Exception:
            cov = 0.0
    else:
        cov = 0.0
    return cov


def compute_axes(changed_py: list[str], full: bool, cov_pct: float) -> dict[str, int]:
    # naive scoring for demo purposes
    base = {a: 90 for a in AXES}
    # penalties
    base["Coding-Style Consistency"] -= ruff_lint(changed_py)
    base["Clarity & Readability"] -= ruff_lint(changed_py) // 2
    base["Complexity Management"] -= radon_complexity(changed_py)
    base["Test Coverage & Quality"] = int(min(100, cov_pct))
    return {k: max(50, v) for k, v in base.items()}


def append_markdown(ts: str, mean: float, axes: dict[str, int], audit_type: str):
    if not SCORE_MD.exists():
        SCORE_MD.write_text(
            "# Quality Scoreboard History\n\n| ISO-Timestamp | Type | Mean | "
            + " | ".join(a.split()[0] for a in AXES)
            + " |\n|---|---|---|"
            + "|".join("---" for _ in AXES)
            + "|\n"
        )
    row = (
        f"| {ts} | {audit_type} | {mean:.2f} | "
        + " | ".join(f"{axes[a]}" for a in AXES)
        + " |\n"
    )
    with SCORE_MD.open("a", encoding="utf8") as fp:
        fp.write(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["delta", "full"], default="delta")
    args = ap.parse_args()
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    last_sha = CACHE.read_text().strip() if CACHE.exists() else ""
    head_sha = shell("git rev-parse HEAD")
    changed_py = (
        git_changed_files(last_sha) if last_sha and args.mode == "delta" else []
    )
    full = args.mode == "full" or not last_sha or not changed_py
    cov = run_tests(changed_py)
    axes = compute_axes(changed_py if not full else ["src"], full, cov)
    mean = sum(axes.values()) / len(axes)
    append_markdown(ts, mean, axes, "baseline" if full else "delta")
    SCORE_JSON.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "audit_type": "baseline" if full else "delta",
                "code_sha": head_sha,
                "base_sha": "" if full else last_sha,
                "mean_score": mean,
                "axes": axes,
                "coverage_pct": cov,
                "low_axes": [a for a, s in axes.items() if s < 90][:4],
            },
            indent=2,
        )
    )
    CACHE.write_text(head_sha)
    print(f"[qa_audit] {('Full' if full else 'Δ')} audit complete. Mean={mean:.2f}")


if __name__ == "__main__":
    main()
