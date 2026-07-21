"""Parse the FRB/US model XML file.

The model file lists ~600 variables; endogenous variables carry a
``standard_equation`` (VAR / backward-looking expectations) and possibly an
``mce_equation`` (model-consistent expectations). Coefficients are stored per
equation as ``coeff`` elements with names like ``y_xgdp(3)`` that appear in the
equation text as ``y_xgdp_3``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree

# Function names allowed in model equations; every other identifier is a variable.
SUPPORTED_FUNCTIONS = ("log", "exp", "max", "min", "abs", "ind_ltezero")


@dataclass
class ModelSpec:
    """Parsed contents of a FRB/US model.xml file."""

    endo_names: list[str]
    equations: list[str]  # python_equation strings, cleaned, same order as endo_names
    exo_names: list[str]
    constants: dict[str, float]
    mce_vars: list[str] = field(default_factory=list)
    stoch_shocks: list[str] = field(default_factory=list)


def _clean(eq: str) -> str:
    """Strip all whitespace from an equation string."""
    return re.sub(r"\s+", "", eq)


def _coeff_name(raw: str) -> str:
    """Convert coefficient names like ``y_xgdp(3)`` to ``y_xgdp_3``."""
    return re.sub(r"y_(.*?)\((\d+)\)", r"y_\1_\2", raw)


def parse_model(filepath: str) -> ModelSpec:
    """Parse a FRB/US model XML file into a :class:`ModelSpec`."""
    root = etree.parse(filepath).getroot()

    endo_names = [n.text for n in root.xpath("./variable[standard_equation]/name")]
    equations = [
        _clean(eq.text)
        for eq in root.xpath("./variable/standard_equation/python_equation")
    ]
    if len(endo_names) != len(equations):
        raise ValueError("Mismatched number of endogenous variables and equations")

    exo_names = [n.text for n in root.xpath("./variable[equation_type='Exogenous']/name")]

    names = [
        _coeff_name(cf.text)
        for cf in root.xpath("./variable/standard_equation/coeff/cf_name")
    ]
    values = [
        float(cf.text) for cf in root.xpath("./variable/standard_equation/coeff/cf_value")
    ]
    constants = dict(zip(names, values, strict=True))

    mce_vars = [
        n.text for n in root.xpath("./variable[mce_equation]/name") if n.text is not None
    ]
    stoch_shocks = [
        n.text
        for n in root.xpath("./variable[stochastic_type!='NO']/name")
        if n.text is not None
    ]

    return ModelSpec(
        endo_names=endo_names,
        equations=equations,
        exo_names=exo_names,
        constants=constants,
        mce_vars=mce_vars,
        stoch_shocks=stoch_shocks,
    )
