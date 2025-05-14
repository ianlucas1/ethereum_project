"""Agent entry-point that performs an INIT-AUDIT before launching the main
analysis pipeline.

This wrapper is intentionally thin so that CI can invoke ``python agent_main.py``
(or package entry-point) and automatically validate Docker buildability prior
to running any heavy data analysis.
"""

from __future__ import annotations

from src.init_audit import run_init_audit

# Perform INIT-AUDIT as early as possible
run_init_audit()

# ---------------------------------------------------------------------------
# Defer heavyweight imports until after the environment has been validated.
# ---------------------------------------------------------------------------
from main import main as _pipeline_main  # noqa: E402  (import after audit)


def main() -> None:  # (imperative naming is fine)
    """Dispatch to the real pipeline *after* the environment audit."""

    _pipeline_main()


if __name__ == "__main__":
    main()
