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


def test_default_paths_resolve():
    """Bundled data accessors resolve to real files (wheel _data/ or vendor/)."""
    from pathlib import Path

    from frbus import default_data_path, default_model_path

    model_path = Path(default_model_path())
    data_path = Path(default_data_path())
    assert model_path.is_file() and model_path.name == "model.xml"
    assert data_path.is_file() and data_path.name == "LONGBASE.TXT"
