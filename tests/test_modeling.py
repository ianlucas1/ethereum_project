import pandas as pd
from src.modeling import fit_ols_hac


def test_ols_beta_two():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [2, 4, 6, 8]})
    res = fit_ols_hac(df, y="y", X=["x"])
    assert abs(res.params["x"] - 2) < 1e-6 