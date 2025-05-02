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
    Keep legacy (df, y, X, …) signature.
    * First try the core implementation.
    * If it skips because the sample is too small, run a quick OLS so
      callers still get an object with `.params`.
    """
    try:
        res = _orig_fit_ols_hac(df[y], df[X], *args, **kwargs)
        if hasattr(res, "params"):
            return res
        # Handle case where res might be the dict itself or nested under 'params'
        if isinstance(res, dict) and 'params' in res:
            coef_dict = res['params']
        elif isinstance(res, dict):
            coef_dict = res
        else:
            # If it's neither a dict nor has .params, and didn't raise Exception,
            # it's an unexpected state. Fallback might still be desired.
            coef_dict = None # Trigger fallback

    except Exception:  # core helper bailed – do simple OLS fallback
        coef_dict = None

    # ---------- fallback path ----------
    # Trigger fallback if core impl failed OR returned unexpected type
    if coef_dict is None:
        # Basic check for sufficient data for OLS itself
        if df.empty or df[y].isnull().all() or df[X].isnull().all().all():
             # Return something predictable but empty if data is unusable
             return pd.Series(dtype=float) # Or raise a more specific error

        Xmat = df[X].copy()
        # Ensure Xmat columns are numeric, handle potential errors
        for col in Xmat.columns:
            Xmat[col] = pd.to_numeric(Xmat[col], errors='coerce')
        Xmat = Xmat.dropna(axis=1, how='all') # Drop fully NA columns if any created

        y_series = pd.to_numeric(df[y], errors='coerce')

        # Align X and y after handling NAs potentially introduced by coercion
        combined = pd.concat([y_series, Xmat], axis=1).dropna()
        if combined.empty or len(combined) <= Xmat.shape[1]: # Check for sufficient rows after dropna
            return pd.Series(dtype=float)

        y_aligned = combined[y]
        X_aligned = combined[X]

        try:
            Xmat_const = sm.add_constant(X_aligned, has_constant="add")
            model = sm.OLS(y_aligned, Xmat_const).fit()
            return model  # has .params
        except Exception as e:
            # Fallback OLS failed, return empty series or raise
            warnings.warn(f"OLS fallback failed: {e}")
            return pd.Series(dtype=float)

    # ---------- dict-wrapper path ----------
    # This path is now only taken if _orig_fit_ols_hac returned a dict
    class _Result:
        def __init__(self, p):
            # Ensure params are in a Series, create from dict if necessary
            if isinstance(p, dict):
                self.params = pd.Series(p)
            else:
                # Should not happen if logic above is correct, but safeguard
                self.params = pd.Series(dtype=float)

    return _Result(coef_dict)


__all__ = ["fit_ols_hac"]

# Other modeling functions (e.g., specific model fits, feature engineering helpers)
# would go here.

# --- Out-of-Sample Rolling Validation --- Function moved to validation.py