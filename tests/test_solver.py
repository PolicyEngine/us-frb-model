"""Unit tests for solver and public-API robustness guards."""

import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix

from frbus.exceptions import ComputationError, FrbusError
from frbus.solver import _preconditioner


def test_preconditioner_scales_rows():
    jac = csr_matrix(np.array([[2.0, 0.0], [0.0, -4.0]]))
    scale = _preconditioner(jac).toarray()
    assert np.allclose(np.diag(scale), [0.5, 0.25])


def test_preconditioner_rejects_zero_rows():
    jac = csr_matrix(np.array([[1.0, 2.0], [0.0, 0.0]]))
    with pytest.raises(ComputationError, match=r"all-zero rows .* \[1\]"):
        _preconditioner(jac)


def test_reversed_simulation_window_is_rejected(model, longbase):
    """start > end used to surface as 'index 0 is out of bounds ... size 0'."""
    with pytest.raises(ValueError, match="precedes start"):
        model.init_trac(pd.Period("2027Q1"), pd.Period("2026Q1"), longbase)


def test_window_outside_the_data_index_names_the_argument(model, longbase):
    """Out-of-range endpoints used to leak 'Period(...) is not in list'."""
    with pytest.raises(ValueError, match=r"end .* is outside the data index"):
        model.init_trac(pd.Period("2026Q1"), pd.Period("2200Q4"), longbase)
    with pytest.raises(ValueError, match=r"start .* is outside the data index"):
        model.init_trac(pd.Period("1900Q1"), pd.Period("2026Q4"), longbase)


def test_non_numeric_input_is_rejected(model, longbase):
    """An object column silently produced an object-dtype solution frame.

    to_numpy() on a frame with one object column returns an object array, so
    the whole solve runs on Python objects and the caller gets back a frame
    whose comparisons and .abs() no longer behave numerically -- a wrong
    answer that looks like a right one.
    """
    data = longbase.copy()
    data["dfpsrp"] = data["dfpsrp"].astype(object)
    with pytest.raises(FrbusError, match="must be entirely numeric"):
        model.init_trac(pd.Period("2026Q1"), pd.Period("2026Q4"), data)
