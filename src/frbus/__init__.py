"""frbus: a modern, from-scratch Python implementation of the FRB/US model.

Semantics follow the Federal Reserve's public-domain pyfrbus package; see
vendor/ and README.md for provenance.
"""

from frbus.data import load_data
from frbus.frbus import Frbus

__all__ = ["Frbus", "load_data"]
__version__ = "0.1.0"
