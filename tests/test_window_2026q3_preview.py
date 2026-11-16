"""Schema and labelling only: the 2026Q3 preview is informational and is not
gated against any published band (it has no pyfrbus reference)."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PREVIEW = json.loads((REPO / "results" / "window_2026q3_preview.json").read_text())


def test_labelled_informational_and_not_cross_validated():
    assert "not cross-validated against pyfrbus" in PREVIEW["label"]
    assert "not gated" in PREVIEW["label"]
    md = (REPO / "results" / "window_2026q3_preview.md").read_text()
    assert "not cross-validated against pyfrbus" in md


def test_schema():
    assert set(PREVIEW["scenarios"]) == {"monetary", "fiscal_egfe", "tax_trp"}
    for runs in PREVIEW["scenarios"].values():
        assert set(runs) == {"2026Q1", "2026Q3"}
        for start, r in runs.items():
            assert r["window"][0] == start
            for k in ("xgdp_pct_peak", "xgap2_peak", "lur_peak", "picxfe_peak"):
                assert {"value", "quarter", "quarter_after_shock"} <= set(r[k])


def test_control_run_is_the_validated_one():
    """The 2026Q1 monetary run is the published, pyfrbus-validated experiment."""
    assert PREVIEW["control_2026q1_monetary_vs_pyfrbus_max_abs"] < 1e-6
