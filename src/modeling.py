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
# implementation expects (y, X, df, …).
from functools import wraps
from typing import Any

_orig_fit_ols_hac = fit_ols_hac  # imported from ols_models above


@wraps(_orig_fit_ols_hac)
def fit_ols_hac(df, y: str, X: list[str], *args: Any, **kwargs: Any):
    """Call the underlying function but keep the (df, y, X, …) signature
    and guarantee the returned object has a `.params` attribute."""
    # The core function now expects y_data, X_data, df, ... - > NO LONGER expects df
    res = _orig_fit_ols_hac(df[y], df[X], *args, **kwargs)

    # If the core impl already returns something with `.params`, forward it.
    if hasattr(res, "params"):
        return res

    # Otherwise assume it's a dict of coefficients and wrap it.
    # Handle case where res might be the dict itself or nested under 'params'
    if isinstance(res, dict) and 'params' in res:
        coef_dict = res['params']
    elif isinstance(res, dict):
        coef_dict = res
    else:
        # If it's neither a dict nor has .params, we have an issue.
        # For now, let's raise an error or handle as appropriate.
        # Assuming it *should* be dict-like if no .params
        # This part might need refinement based on what _orig_fit_ols_hac actually returns
        raise TypeError(f"Unexpected return type from underlying fit_ols_hac: {type(res)}")

    class _Result:
        def __init__(self, params_dict, original):
            self.params = pd.Series(params_dict)
            self._original = original # Store original result if needed later

    return _Result(coef_dict, res)


__all__ = ["fit_ols_hac"]

# Other modeling functions (e.g., specific model fits, feature engineering helpers)
# would go here.

# --- Out-of-Sample Rolling Validation --- Function moved to validation.py