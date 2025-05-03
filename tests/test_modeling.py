import pandas as pd
from src.ols_models import fit_ols_hac


def test_ols_beta_two():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "y": [2, 4, 6, 8, 10, 12]})
    y_series = df["y"]
    X_df = df[["x"]]
    res = fit_ols_hac(y=y_series, X=X_df, add_const=False, lags=0)
    assert "params" in res, "Result dictionary should contain 'params' key"
    assert "x" in res["params"], "Params dictionary should contain 'x' key"
    assert abs(res["params"]["x"] - 2) < 1e-6
