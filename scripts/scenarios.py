"""Reference shock scenarios shared by the vendor generator and the gates.

Each scenario is defined once here and executed identically against (a) the
Fed's vendored pyfrbus (scripts/generate_vendor_reference.sh, which writes the
committed reference CSVs) and (b) this implementation (tests/test_shock.py),
so the cross-validation gates are exactly like-for-like.

Only pandas operations are used so this module also runs inside the vendor's
pinned pandas<2 environment.
"""

START = "2026Q1"
END = "2030Q4"

#: scenario name -> (data settings applied before init_trac,
#:                   shock applied to the with-adds baseline)
SCENARIOS = [
    # 100bp shock to the inertial Taylor rule (the original reference).
    "monetary",
    # Fiscal lever: 1% shock to federal expenditures ex. transfers (egfe).
    "fiscal_egfe",
    # Tax lever: +2pp shock to the personal average tax rate (trp).
    "tax_trp",
    # Different policy rule: non-inertial Taylor rule, 100bp shock.
    "taylor_noninertial",
]


def set_policy(name, data, start, end):
    """Apply pre-init_trac policy settings for scenario ``name`` in place."""
    # Standard demo fiscal configuration: surplus-ratio targeting.
    data.loc[start:end, "dfpdbt"] = 0
    data.loc[start:end, "dfpsrp"] = 1
    if name == "taylor_noninertial":
        data.loc[start:end, "dmptay"] = 1
        data.loc[start:end, "dmpintay"] = 0
    elif name not in ("monetary", "fiscal_egfe", "tax_trp"):
        raise ValueError(f"unknown scenario: {name}")


def apply_shock(name, with_adds, start, end):
    """Apply the scenario shock to the with-adds baseline in place."""
    if name == "monetary":
        with_adds.loc[start, "rffintay_aerr"] += 1
    elif name == "fiscal_egfe":
        with_adds.loc[start, "egfe_aerr"] += 0.01
    elif name == "tax_trp":
        with_adds.loc[start, "trp_aerr"] += 0.02
    elif name == "taylor_noninertial":
        with_adds.loc[start, "rfftay_aerr"] += 1
    else:
        raise ValueError(f"unknown scenario: {name}")
