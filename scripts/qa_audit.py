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
import datetime
import json
import logging  # Added import
import pathlib
import subprocess  # nosec B404

# Configure basic logging for error messages from shell commands
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


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


def shell(cmd_list: list[str]) -> str:
    # The first item in cmd_list is the command, subsequent items are arguments.
    # text=True decodes stdout/stderr as text (utf-8 by default).
    try:
        # Using check=True makes subprocess.run raise CalledProcessError on non-zero exit.
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)  # nosec B603
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Log the error details from CalledProcessError
        logging.error(
            f"Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}.\n"
            f"Stdout: {e.stdout.strip()}\n"
            f"Stderr: {e.stderr.strip()}"
        )
        raise  # Re-raise the original CalledProcessError


def git_changed_files(since_sha: str) -> list[str]:
    diff = shell(["git", "diff", "--name-only", since_sha, "HEAD"])
    return [f for f in diff.splitlines() if f.endswith(".py")]


def ruff_lint(files: list[str]) -> int:
    if not files:
        return 0
    try:
        shell(["ruff", "check", *files])  # Pass files as a list
        return 0
    except subprocess.CalledProcessError:
        return 10  # simple penalty


def mypy_check(
    files: list[str],
) -> int:  # This function is defined but not used in main()
    if not files:
        return 0
    try:
        shell(["mypy", "--strict", *files])  # Pass files as a list
        return 0
    except subprocess.CalledProcessError:
        return 10


def radon_complexity(files: list[str]) -> int:
    if not files:
        return 0
    try:
        out = shell(["radon", "cc", "-s", *files])  # Pass files as a list
        # Ensure there's output to process
        if not out.strip():  # Check if output is empty or just whitespace
            logging.warning(
                f"Radon produced no output for files: {files}. Assuming good complexity."
            )
            return 0

        scores = []
        for line in out.splitlines():
            parts = line.split()
            if (
                parts and parts[-1].isalpha() and "A" <= parts[-1].upper() <= "F"
            ):  # Check if last part is a letter grade
                scores.append(parts[-1].upper())  # Make it uppercase for consistency

        if not scores:  # No valid scores found in output
            logging.warning(
                f"Radon output did not contain valid complexity scores: {out}. Assuming good complexity."
            )
            return 0

        worst = max(
            scores, default="A"
        )  # Get the lexicographically largest (worst) grade
        penalty = (ord(worst) - ord("A")) * 5
        return penalty
    except subprocess.CalledProcessError:
        return 5  # Return a default penalty on error
    except ValueError:  # Catch potential errors if max() gets an empty sequence (though default handles this)
        logging.warning(
            f"Radon complexity calculation encountered an issue for files: {files}. Assuming good complexity."
        )
        return 0


def run_tests(changed: list[str]) -> float:
    # Pytest can often figure out which tests to run based on changed files
    # if SCM integration is set up or by passing files as arguments.
    # For coverage, it's usually more robust to specify the source directory.
    coverage_target = "src"

    cmd = ["pytest", f"--cov={coverage_target}", "-q"]
    # If `changed` files are provided, you might pass them to pytest to focus tests.
    # This script's original logic seemed to use `changed` to alter the --cov target,
    # which can be problematic. Here, we always cover `src` and optionally pass
    # changed files to pytest for test selection, if desired.
    # For simplicity in this refactor, we'll keep the command basic.
    # If `changed` is non-empty and you want pytest to specifically run tests for those, add:
    # if changed:
    #    cmd.extend(changed)

    shell(cmd)  # Run pytest command

    cov_xml = ROOT / "coverage.xml"
    if cov_xml.exists():
        txt = cov_xml.read_text()
        try:
            # More robust parsing for coverage percentage
            import defusedxml.ElementTree as ET

            tree = ET.parse(cov_xml)
            root_xml = tree.getroot()
            coverage_element = root_xml.find("coverage")
            if coverage_element is not None and "line-rate" in coverage_element.attrib:
                cov = float(coverage_element.attrib["line-rate"]) * 100
            else:  # Fallback to original string splitting if structure is different
                logging.warning(
                    "Could not find 'coverage[@line-rate]' in coverage.xml, falling back to string split."
                )
                cov = float(txt.split('line-rate="')[1].split('"')[0]) * 100
        except Exception as e:
            logging.error(
                f"Failed to parse coverage.xml: {e}. Defaulting coverage to 0.0."
            )
            cov = 0.0
    else:
        logging.warning("coverage.xml not found. Defaulting coverage to 0.0.")
        cov = 0.0
    return cov


def compute_axes(changed_py: list[str], full: bool, cov_pct: float) -> dict[str, int]:
    # naive scoring for demo purposes
    base = {a: 90 for a in AXES}
    # penalties
    files_to_scan = (
        changed_py if not full and changed_py else ["src"]
    )  # Scan 'src' for full or if no changed files for delta

    base["Coding-Style Consistency"] -= ruff_lint(files_to_scan)
    base["Clarity & Readability"] -= ruff_lint(files_to_scan) // 2
    base["Complexity Management"] -= radon_complexity(files_to_scan)
    base["Test Coverage & Quality"] = int(
        min(100, cov_pct)
    )  # Ensure it doesn't exceed 100
    return {k: max(50, v) for k, v in base.items()}  # Ensure scores don't drop below 50


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

    # Create a timezone-aware datetime object in UTC
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Format it to ISO 8601 with 'Z' for UTC
    ts = now_utc.isoformat(timespec="seconds").replace("+00:00", "Z")

    last_sha = ""
    if CACHE.exists():
        last_sha = CACHE.read_text().strip()

    try:
        head_sha = shell(["git", "rev-parse", "HEAD"])
    except subprocess.CalledProcessError:
        logging.error("Failed to get current git HEAD SHA. Exiting.")
        return  # Exit if git command fails

    changed_py: list[str] = []
    if last_sha and args.mode == "delta":
        try:
            changed_py = git_changed_files(last_sha)
        except subprocess.CalledProcessError:
            logging.warning(
                f"Failed to get changed files since {last_sha}. Assuming full audit needed."
            )
            # Proceed as if full audit is needed if diff fails

    # Determine if a full audit is needed
    # Full audit if:
    # 1. --mode=full is specified
    # 2. There was no last_sha (first run)
    # 3. In delta mode, but no python files were changed (or diff failed and changed_py is empty)
    #    This ensures that if only non-Python files changed, we don't skip the audit summary update.
    #    The tools (ruff, radon) will run on 'src' if changed_py is empty for `compute_axes`.
    full_audit_needed = args.mode == "full" or not last_sha
    if args.mode == "delta" and last_sha and not changed_py:
        logging.info(
            "Delta mode: No Python files changed since last audit, or diff failed. Running checks on 'src'."
        )
        # Tools will scan 'src' via compute_axes logic, but it's not a "full baseline" in terms of changed files.
        # The `audit_type` reflects the mode.

    audit_type_str = (
        "baseline" if full_audit_needed else args.mode
    )  # "delta" or "baseline"

    # Files to pass to tools for scoring. If delta and changed_py has files, use them.
    # Otherwise (full_audit_needed or delta with no changed .py files), tools will scan 'src'.
    files_for_scoring = changed_py if args.mode == "delta" and changed_py else []

    cov = run_tests(
        changed_py
    )  # run_tests might use `changed_py` to focus tests, but covers 'src'
    axes = compute_axes(
        files_for_scoring, full_audit_needed, cov
    )  # files_for_scoring ensures tools run on 'src' if needed
    mean = sum(axes.values()) / len(axes) if axes else 0.0

    append_markdown(ts, mean, axes, audit_type_str)

    SCORE_JSON.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "audit_type": audit_type_str,
                "code_sha": head_sha,
                "base_sha": "" if full_audit_needed else last_sha,
                "mean_score": mean,
                "axes": axes,
                "coverage_pct": cov,
                "low_axes": [a for a, s in axes.items() if s < 90][:4],
            },
            indent=2,
        )
    )
    CACHE.write_text(head_sha)
    print(f"[qa_audit] {audit_type_str.capitalize()} audit complete. Mean={mean:.2f}")


if __name__ == "__main__":
    main()
