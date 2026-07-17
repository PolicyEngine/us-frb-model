from pathlib import Path

import pytest

from frbus import Frbus, load_data

REPO = Path(__file__).resolve().parents[1]
MODEL_XML = REPO / "vendor" / "pyfrbus_package" / "models" / "model.xml"
LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"


@pytest.fixture(scope="session")
def model() -> Frbus:
    return Frbus(str(MODEL_XML))


@pytest.fixture(scope="session")
def longbase():
    return load_data(str(LONGBASE))
