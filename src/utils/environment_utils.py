"""Utility functions for detecting and preparing the runtime environment.

This module will be expanded to include routines that check for container
configuration files (e.g. Dockerfile or docker-compose.yml) and attempt to
build a local test image so that the agent can execute within a controlled
containerised environment.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 (subprocess is required for docker build)
from datetime import datetime
from pathlib import Path

__all__: list[str] = [
    "check_and_build_docker_image",
]

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _append_to_log(log_file: Path, message: str) -> None:
    """Append *message* to *log_file*, creating directories as needed."""

    # Ensure parent directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with log_file.open("a", encoding="utf-8") as fp:
        fp.write(f"[{timestamp}] {message}\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_and_build_docker_image(repo_root: Path) -> bool:
    """Detect container configuration files and attempt to build a test image.

    This utility checks whether Docker is installed, then looks for either a
    ``Dockerfile`` or ``docker-compose.yml`` in *repo_root*. If neither is
    present, it returns ``False`` without further action. When a configuration
    file exists, the function invokes ``docker build -t agent_test .`` within
    the repository root. All output is captured and appended to
    ``logs/environment.log`` under *repo_root*.

    A boolean indicating whether the image was built successfully is returned.
    """

    log_file = repo_root / "logs" / "environment.log"

    # --------------------------------------------------------------------
    # Check Docker availability
    # --------------------------------------------------------------------
    if shutil.which("docker") is None:
        _append_to_log(log_file, "Docker CLI not found in PATH - skipping image build.")
        return False

    # --------------------------------------------------------------------
    # Detect Docker-related config files
    # --------------------------------------------------------------------
    dockerfile = repo_root / "Dockerfile"
    compose_file = repo_root / "docker-compose.yml"

    if not (dockerfile.exists() or compose_file.exists()):
        _append_to_log(
            log_file, "No Docker configuration detected - skipping image build."
        )
        return False

    # --------------------------------------------------------------------
    # Attempt to build image
    # --------------------------------------------------------------------
    cmd = ["docker", "build", "-t", "agent_test", "."]
    try:
        proc = subprocess.run(  # nosec B603 (controlled parameters)
            cmd,
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _append_to_log(
            log_file, f"Docker image build succeeded. Output:\n{proc.stdout}"
        )
        return True
    except subprocess.CalledProcessError as exc:
        output = exc.stdout or ""
        _append_to_log(
            log_file,
            f"Docker image build failed with exit code {exc.returncode}. Output:\n{output}",
        )
        return False
    except Exception as exc:
        _append_to_log(log_file, f"Unexpected error during docker build: {exc}")
        return False
