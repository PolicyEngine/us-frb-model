import numpy as np
import pandas as pd


def test_load_longbase(longbase):
    assert isinstance(longbase.index, pd.PeriodIndex)
    assert longbase.index.freqstr in ("Q", "Q-DEC")
    assert longbase.index[0] == pd.Period("1962Q1")
    assert longbase.index[-1] >= pd.Period("2100Q1")
    assert longbase["xgdp"].dtype == np.float64
    # Recent history should be present and positive
    assert longbase.loc[pd.Period("2025Q1"), "xgdp"] > 0
