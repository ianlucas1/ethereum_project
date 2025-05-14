"""Initial environment audit for the agent runtime.

This lightweight module is imported at the very beginning of the agent startup
sequence (see ``agent_main.py``). It checks whether a Docker test image can be
built successfully and, if not, records a *blocked* bootstrap state so that the
agent does not proceed with an invalid environment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from src.utils.environment_utils import check_and_build_docker_image

BLOCKED_REASON: Final[str] = "Blocked-EnvironmentConfig"


# ---------------------------------------------------------------------------
# Helper utilities (local fall-backs - the full agent runtime includes richer
# coordination helpers, but these minimal versions are sufficient for CI).
# ---------------------------------------------------------------------------


def _append_human_request(tag: str, note: str, repo_root: Path) -> None:
    """Append a human-action request to *human_requests.md*."""

    hr_file = repo_root / "human_requests.md"
    with hr_file.open("a", encoding="utf-8") as fp:
        fp.write(f"- **{tag}**: {note}\n")


def _enter_blocked_state(tag: str, repo_root: Path) -> None:
    """Persist *tag* in ``.agent_workspace/session_bootstrap.json``."""

    ws_dir = repo_root / ".agent_workspace"
    ws_dir.mkdir(parents=True, exist_ok=True)
    session_file = ws_dir / "session_bootstrap.json"
    with session_file.open("w", encoding="utf-8") as fp:
        json.dump({"blocked_state": tag}, fp, indent=2)


# ---------------------------------------------------------------------------
# Public routine
# ---------------------------------------------------------------------------


def run_init_audit() -> None:  # (imperative mood acceptable for script entry)
    """Run startup checks (Docker build) and record any blocking issues."""

    # Assuming src/ directory under the project root, step one level up to repo
    repo_root = Path(__file__).resolve().parent.parent

    docker_ok = check_and_build_docker_image(repo_root)
    if docker_ok:
        return  # Happy path 💚

    human_note = (
        "Docker image build failed during INIT-AUDIT; "
        "see logs/environment.log for details. "
        "Please fix Docker context or set prefer_docker=false."
    )

    _append_human_request(BLOCKED_REASON, human_note, repo_root)
    _enter_blocked_state(BLOCKED_REASON, repo_root)
