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


def test_used_exos_match_whole_identifiers(model):
    """Every retained exogenous variable must appear as a whole identifier in
    some equation -- substring hits (e.g. "rff" inside "rffintay") must not
    count. Verified against the raw equation text with word boundaries."""
    import re

    spec = model.spec
    eqs = [
        eq + f"+{endo}_trac"
        for eq, endo in zip(spec.equations, spec.endo_names, strict=True)
    ]
    declared = set(spec.exo_names)
    kept = [
        exo
        for exo in model._orig_exo_names
        if exo in declared  # skip generated _aerr/_trac names
    ]
    for exo in kept:
        pat = re.compile(rf"(?<![\w]){re.escape(exo)}(?![\w])")
        assert any(pat.search(eq) for eq in eqs), (
            f"{exo} kept as used exo but never appears as a whole token"
        )
