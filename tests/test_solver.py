"""Unit tests for solver robustness guards."""

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from frbus.exceptions import ComputationError
from frbus.solver import _preconditioner


def test_preconditioner_scales_rows():
    jac = csr_matrix(np.array([[2.0, 0.0], [0.0, -4.0]]))
    scale = _preconditioner(jac).toarray()
    assert np.allclose(np.diag(scale), [0.5, 0.25])


def test_preconditioner_rejects_zero_rows():
    jac = csr_matrix(np.array([[1.0, 2.0], [0.0, 0.0]]))
    with pytest.raises(ComputationError, match=r"all-zero rows .* \[1\]"):
        _preconditioner(jac)
