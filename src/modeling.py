# src/modeling.py

# Keeping these imports in case other modeling functions are added later.
import pandas as pd # Generally useful
import numpy as np # Generally useful
import statsmodels.api as sm # Likely useful for other models
from statsmodels.tools.sm_exceptions import SpecificationWarning, InterpolationWarning
import warnings

# Re-export for backward compatibility
from src.ts_models import fit_ols_hac

__all__ = ["fit_ols_hac"]

# Other modeling functions (e.g., specific model fits, feature engineering helpers)
# would go here.

# --- Out-of-Sample Rolling Validation --- Function moved to validation.py