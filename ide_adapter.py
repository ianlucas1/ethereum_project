"""
Thin abstraction layer so the agent can call Cursor-specific helpers when
running inside the Cursor IDE, but degrade gracefully to headless CLI mode.
"""

from typing import Optional

__all__ = ["open_file", "show_message", "get_active_model"]

try:
    # Replace with the real Cursor SDK import when available
    import cursor_api as _cursor

    _HAS_CURSOR = True
except ImportError:
    _HAS_CURSOR = False

# --------------------------------------------------------------------------- #
# Public helpers                                                              #
# --------------------------------------------------------------------------- #


def open_file(path: str) -> None:
    """Open a file in the editor (NO-OP in headless mode)."""

    if _HAS_CURSOR:
        _cursor.open_file(path)  # type: ignore[attr-defined]


def show_message(msg: str) -> None:
    """Display an informational message to the user/IDE."""

    if _HAS_CURSOR:
        _cursor.show_message(msg)  # type: ignore[attr-defined]
    else:
        print(f"[AGENT] {msg}")


def get_active_model() -> Optional[str]:
    """Return the IDE-selected LLM model or None if not available."""

    if _HAS_CURSOR:
        return _cursor.get_active_model()  # type: ignore[attr-defined]
    return None
