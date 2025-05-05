"""Core modeling functions and re-exports for the ethereum_project."""

from __future__ import annotations

# Keeping these imports in case other modeling functions are added later.

# Re-export for backward compatibility
# from src.ts_models import fit_ols_hac

# Back-compat wrapper: allow (df, y, X, …) even though the core
# implementation expects (y, X, df, …). -> Now expects (y_data, X_data)


__all__: list[str] = []

# Other modeling functions (e.g., specific model fits, feature engineering helpers)
# would go here.

# --- Out-of-Sample Rolling Validation --- Function moved to validation.py
