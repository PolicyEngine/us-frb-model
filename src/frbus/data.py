"""Loading of FRB/US datasets (LONGBASE.TXT format)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from frbus.exceptions import MissingDataError

# In a wheel install the files are shipped at frbus/_data/ (see pyproject
# force-include); in an editable/clone install they live under vendor/.
_PKG_DATA = Path(__file__).resolve().parent / "_data"
_VENDOR = Path(__file__).resolve().parents[2] / "vendor"
_VENDOR_PATHS = {
    "model.xml": _VENDOR / "pyfrbus_package" / "models" / "model.xml",
    "LONGBASE.TXT": _VENDOR / "data_only_package" / "LONGBASE.TXT",
}


def _bundled(filename: str) -> str:
    for candidate in (_PKG_DATA / filename, _VENDOR_PATHS[filename]):
        if candidate.is_file():
            return str(candidate)
    raise MissingDataError(filename)


def default_model_path() -> str:
    """Path to the bundled FRB/US ``model.xml``."""
    return _bundled("model.xml")


def default_data_path() -> str:
    """Path to the bundled ``LONGBASE.TXT`` baseline dataset."""
    return _bundled("LONGBASE.TXT")


def load_data(filename: str) -> pd.DataFrame:
    """Load a FRB/US dataset into a DataFrame with a quarterly PeriodIndex."""
    data = pd.read_csv(filename, index_col=0)
    data.index = pd.PeriodIndex(data.index, freq="Q")
    data.index.name = None
    data.columns = [col.lower() for col in data.columns]
    return data.astype(np.float64)
