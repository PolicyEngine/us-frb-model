import pytest

from frbus.parse import parse_model
from tests.conftest import MODEL_XML


def test_model_counts():
    spec = parse_model(str(MODEL_XML))
    assert len(spec.endo_names) == 284
    assert len(spec.equations) == 284
    assert len(spec.exo_names) == 83
    assert len(spec.constants) > 500


def test_known_equation():
    spec = parse_model(str(MODEL_XML))
    i = spec.endo_names.index("dmptmax")
    assert spec.equations[i] == "dmptmax-dmptmax_aerr=(max((dmptlur),(dmptpi)))"


def test_coefficient_names_normalized():
    spec = parse_model(str(MODEL_XML))
    assert all("(" not in name for name in spec.constants)
    assert "y_dmptlur_1" in spec.constants


def test_mce_stub():
    from frbus import Frbus

    with pytest.raises(NotImplementedError):
        Frbus(str(MODEL_XML), mce="mcap+wp")


def test_model_setup(model):
    # aerr and trac terms are exogenous
    assert "xgdp_trac" in model.exo_names
    assert "xgdp_aerr" in model.exo_names
    assert "xgdp" in model.endo_names
