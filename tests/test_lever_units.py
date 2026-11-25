"""What one unit of each commonly shocked add-factor does, and whether it stacks.

``<name>_aerr`` is added to the right-hand side of the equation for ``<name>``
as that equation is written in ``model.xml``, so its unit is the unit of the
equation's left-hand side: a level for ``trp`` or ``poil``, a log level for
``ecnia``, quarterly log growth for ``egfe``. Holding the same add-factor for
several quarters then does very different things lever by lever. VALIDATION.md
("Period stacking") had this for ``rffintay_aerr`` and ``egfe_aerr`` only; this
file pins it for every lever PolicyEngine Macro's ``frbus_shock`` exposes
(PolicyEngine/macro#212), so a wrapper's units strings can be checked against
the model rather than against prose.

The numbers are this implementation's on the October 2026 LONGBASE, shock from
2026Q1 under the demo fiscal settings. They are regression pins, not published
values: the equations they follow from are the Board's, and the solve is gated
against pyfrbus elsewhere (tests/test_shock.py).
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scenarios  # noqa: E402

START = pd.Period("2026Q1")
END = pd.Period("2027Q1")

# lever -> (left-hand side of its equation in model.xml, as parsed; response
#           unit; shock size per quarter; policy settings; then the response of
#           the lever's own variable: one shocked quarter, in q1 and in q4;
#           four shocked quarters, in q4; and real GDP in q1 after one shocked
#           quarter, % of baseline)
#
# Response units: "pp" is a percentage-point deviation (the funds rate; tax
# rates are stored as decimals and scaled by 100 here), "pct" is a % deviation
# from baseline, "usd" is dollars per barrel.
LEVERS = {
    "rffintay_aerr": ("rffintay-rffintay_aerr", "pp", 1.0, "monetary",
                      1.0001, 0.4912, 2.9713, 0.0006),
    "rfftay_aerr": ("rfftay-rfftay_aerr", "pp", 1.0, "taylor_noninertial",
                    1.0009, -0.1575, 0.5482, 0.0006),
    "egfe_aerr": ("(log(egfe)-(log(egfe(-1))))-egfe_aerr", "pct", 0.01, "monetary",
                  1.0013, 0.5595, 2.8958, 0.0373),
    "egse_aerr": ("(log(egse)-(log(egse(-1))))-egse_aerr", "pct", 0.01, "monetary",
                  1.0105, 0.7537, 3.7137, 0.0343),
    "trp_aerr": ("trp-trp_aerr", "pp", 0.01, "monetary",
                 0.9927, 0.3385, 2.3254, -0.1157),
    "trci_aerr": ("trci-trci_aerr", "pp", 0.01, "monetary",
                  1.0000, 0.5138, 2.9485, 0.0000),
    "ecnia_aerr": ("log(ecnia)-ecnia_aerr", "pct", 0.01, "monetary",
                   1.0603, 1.0074, 4.1930, 0.5962),
    "ebfi_aerr": ("(log(ebfi)-log(ebfi(-1)))-ebfi_aerr", "pct", 0.01, "monetary",
                  1.0050, 1.7941, 5.9490, 0.1166),
    "poil_aerr": ("poil-poil_aerr", "usd", 10.0, "monetary",
                  10.0262, -0.0032, 9.9985, -0.0233),
}

# Levers whose add-factor does NOT accumulate when held: the equation has no
# lag of its own variable, so four shocked quarters hold the variable near the
# one-quarter response instead of building on it.
NON_STACKING = {"rfftay_aerr", "poil_aerr"}


def _lever_variable(lever: str) -> str:
    return "rff" if lever in ("rffintay_aerr", "rfftay_aerr") else lever.removesuffix("_aerr")


@pytest.fixture(scope="module")
def baselines(model, longbase):
    out = {}
    for policy in ("monetary", "taylor_noninertial"):
        data = longbase.copy()
        scenarios.set_policy(policy, data, str(START), str(END))
        out[policy] = model.init_trac(START, END, data)
    return out


def _response(model, base, lever, unit, size, quarters):
    shocked = base.copy()
    shocked.loc[START : START + quarters - 1, lever] += size
    sim = model.solve(START, END, shocked)
    var = _lever_variable(lever)
    own, ref = sim.loc[START:END, var], base.loc[START:END, var]
    if unit == "pct":
        path = 100 * (own / ref - 1)
    elif unit == "pp":
        path = (own - ref) * (1 if var == "rff" else 100)
    else:
        path = own - ref
    gdp = 100 * (sim.loc[START:END, "xgdp"] / base.loc[START:END, "xgdp"] - 1)
    return path.to_numpy(), gdp.to_numpy()


@pytest.fixture(scope="module")
def responses(model, baselines):
    out = {}
    for lever, (_, unit, size, policy, *_rest) in LEVERS.items():
        base = baselines[policy]
        out[lever] = {
            n: _response(model, base, lever, unit, size, n) for n in (1, 4)
        }
    return out


@pytest.mark.parametrize("lever", LEVERS)
def test_add_factor_enters_the_equation_as_written(model, lever):
    """The unit of an add-factor is the unit of its equation's left-hand side."""
    name = lever.removesuffix("_aerr")
    equation = model.spec.equations[model.spec.endo_names.index(name)]
    assert equation.split("=")[0] == LEVERS[lever][0]


@pytest.mark.parametrize("lever", LEVERS)
def test_one_unit_of_each_lever(responses, lever):
    """Pinned: the lever's own variable after one and after four shocked quarters."""
    _, _, _, _, q1, q4, held_q4, gdp_q1 = LEVERS[lever]
    one, gdp = responses[lever][1]
    held, _ = responses[lever][4]
    assert one[0] == pytest.approx(q1, abs=2e-4)
    assert one[3] == pytest.approx(q4, abs=2e-4)
    assert held[3] == pytest.approx(held_q4, abs=2e-4)
    assert gdp[0] == pytest.approx(gdp_q1, abs=2e-4)
    # The first shocked quarter is the same experiment either way.
    assert held[0] == pytest.approx(one[0], abs=1e-9)


@pytest.mark.parametrize("lever", LEVERS)
def test_which_levers_stack(responses, lever):
    """Holding an add-factor four quarters: 2.3x to 5.9x the impact, or about 1x.

    Seven of the nine levers have their own variable's lag (or its growth) in
    the equation, so the fourth shocked quarter sits far above the first. The
    non-inertial Taylor rule and the oil-price identity have no such lag: four
    shocked quarters never take the variable above the one-quarter response.
    """
    one, _ = responses[lever][1]
    held, _ = responses[lever][4]
    ratio = held[3] / one[0]
    if lever in NON_STACKING:
        assert held[:4].max() == pytest.approx(one[0], rel=1e-6)
        assert ratio < 1.0
    else:
        assert ratio > 2.3, f"{lever}: held q4 is {ratio:.2f}x the impact"
        assert held[3] == held[:4].max()


def test_impact_units(responses):
    """What the shock sizes above mean on impact, to the stated rounding.

    +1.0 on either Taylor rule is +100bp on the funds rate; +0.01 on a tax
    rate is +1 percentage point; +0.01 on a log-growth or log-level equation
    is about +1% on the level; +10 on the oil price is +$10 a barrel.
    """
    for lever in ("rffintay_aerr", "rfftay_aerr", "trp_aerr", "trci_aerr",
                  "egfe_aerr", "egse_aerr", "ebfi_aerr"):
        assert responses[lever][1][0][0] == pytest.approx(1.0, abs=0.011), lever
    # Consumption is 69% of GDP and feeds back on itself within the quarter,
    # so +0.01 lands at +1.06%, and moves real GDP by 0.60% in that quarter.
    assert responses["ecnia_aerr"][1][0][0] == pytest.approx(1.06, abs=0.005)
    assert responses["ecnia_aerr"][1][1][0] == pytest.approx(0.60, abs=0.005)
    assert responses["poil_aerr"][1][0][0] == pytest.approx(10.0, abs=0.05)


def test_single_impulses_that_do_not_decay(responses):
    """Two levers stay up, or keep rising, after a single shocked quarter.

    ``ecnia`` is a random walk in logs (its own lag has coefficient 1), so one
    impulse is close to a permanent level shift. ``ebfi`` growth depends on
    its own two lags (0.52 and 0.30, each times a 0.62 weight), so one impulse
    keeps raising the level:
    +1.0% on impact, +1.8% a year later. "0.01 is 1% higher investment" is
    true of the first quarter only.
    """
    ecnia, _ = responses["ecnia_aerr"][1]
    ebfi, _ = responses["ebfi_aerr"][1]
    assert ecnia[4] > 0.9 * ecnia[0]
    assert all(b > a for a, b in zip(ebfi[:4], ebfi[1:5], strict=True))
    assert ebfi[4] == pytest.approx(1.847, abs=2e-3)


def test_levels_the_units_are_read_against(baselines):
    """The 2026Q1 baseline levels VALIDATION.md quotes beside the table.

    Federal purchases are 4.5% of real GDP (4.3% in nominal terms), so 0.01 on
    ``egfe_aerr`` is about 0.045% of GDP; the oil price is $66 a barrel, so
    +10 on ``poil_aerr`` is +15%.
    """
    base = baselines["monetary"].loc[START]
    assert base["egfe"] / base["xgdp"] == pytest.approx(0.0451, abs=5e-4)
    assert base["egfen"] / base["xgdpn"] == pytest.approx(0.0427, abs=5e-4)
    assert base["poil"] == pytest.approx(65.97, abs=0.05)
    assert 100 * 10 / base["poil"] == pytest.approx(15.2, abs=0.1)
