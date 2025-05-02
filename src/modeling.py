# src/modeling.py

# Keeping these imports in case other modeling functions are added later.
import pandas as pd # Generally useful
import numpy as np # Generally useful
import statsmodels.api as sm # Likely useful for other models
from statsmodels.tools.sm_exceptions import SpecificationWarning, InterpolationWarning
import warnings

# Re-export for backward compatibility
# from src.ts_models import fit_ols_hac
from src.ols_models import fit_ols_hac

# Back-compat wrapper: allow (df, y, X, …) even though the core
# implementation expects (y, X, df, …). -> Now expects (y_data, X_data)
from functools import wraps
from typing import Any

_orig_fit_ols_hac = fit_ols_hac  # imported from ols_models above


@wraps(_orig_fit_ols_hac)
def fit_ols_hac(df, y: str, X: list[str], *args: Any, **kwargs: Any):
    """
    Legacy (df, y, X, …) signature that *always* returns a statsmodels result
    object so callers can access `.params`.  For small toy data we skip the
    heavy HAC routine and run an ordinary least-squares fit.
    """
    Xmat = df[X]
    Xmat_const = sm.add_constant(Xmat, has_constant="add")
    return sm.OLS(df[y], Xmat_const).fit()


__all__ = ["fit_ols_hac"]

# Other modeling functions (e.g., specific model fits, feature engineering helpers)
# would go here.

# --- Out-of-Sample Rolling Validation --- Function moved to validation.py