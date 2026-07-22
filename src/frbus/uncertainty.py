"""Public uncertainty surface: percentile bands from stochastic simulations.

Wraps ``Frbus.stochsim`` (a seeded joint historical-residual bootstrap) into a
band-summary API: given a shock scenario, run N stochastic replications and
return percentile bands (e.g. 68/90% coverage) for the requested series,
together with the deterministic path and an honest account of how many
replications converged and how many failed (and why).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from frbus.exceptions import ConvergenceError

#: Headline series used when the caller does not pass ``series``.
HEADLINE_SERIES = ["xgdp", "xgap2", "lur", "picxfe", "rff"]


@dataclass(frozen=True)
class StochsimBands:
    """Result of :func:`stochsim_bands`.

    Attributes
    ----------
    bands:
        Quarterly frame over the simulation window with MultiIndex columns
        ``(series, band)`` where ``band`` is ``lower<c>``/``upper<c>`` for
        each coverage level ``c`` plus ``median`` — e.g.
        ``bands[("xgdp", "lower90")]``. Computed from successful replications
        only.
    deterministic:
        The deterministic (no stochastic shocks) solution for the same series
        over the same window.
    nrepl / n_success / n_failed:
        Requested replication count and how many converged / failed.
    failures:
        One ``"ErrorType: message"`` string per failed replication.
    seed / coverage / series:
        The inputs that produced this result, for reproducibility.
    """

    bands: pd.DataFrame
    deterministic: pd.DataFrame
    nrepl: int
    n_success: int
    n_failed: int
    failures: list[str] = field(default_factory=list)
    seed: int = 1000
    coverage: tuple[float, ...] = (68.0, 90.0)
    series: tuple[str, ...] = ()

    @property
    def failure_rate(self) -> float:
        return self.n_failed / self.nrepl


def _band_quantiles(coverage: tuple[float, ...]) -> dict[str, float]:
    """Map band labels to quantile levels for the given coverage levels."""
    for c in coverage:
        if not 0.0 < c < 100.0:
            raise ValueError(f"coverage levels must be in (0, 100), got {c}")
    labels = {"median": 0.5}
    for c in coverage:
        tail = (1.0 - c / 100.0) / 2.0
        labels[f"lower{c:g}"] = tail
        labels[f"upper{c:g}"] = 1.0 - tail
    return labels


def stochsim_bands(
    model,
    nrepl: int,
    input_data: pd.DataFrame,
    simstart,
    simend,
    residstart,
    residend,
    *,
    series: list[str] | None = None,
    coverage: tuple[float, ...] = (68.0, 90.0),
    seed: int = 1000,
    options: dict | None = None,
) -> StochsimBands:
    """Run ``nrepl`` bootstrap replications and summarize as percentile bands.

    Reproducible for a fixed ``seed``. Replications whose solver fails are
    counted and reported in ``failures``, never silently dropped; bands are
    computed over the successful replications. Raises
    :class:`~frbus.exceptions.ConvergenceError` if every replication fails.
    """
    series = list(series) if series is not None else list(HEADLINE_SERIES)
    unknown = [s for s in series if s not in model.endo_names]
    if unknown:
        raise ValueError(f"series not among endogenous variables: {unknown}")
    quantiles = _band_quantiles(tuple(coverage))

    periods = pd.period_range(simstart, simend, freq="Q")
    deterministic = model.solve(simstart, simend, input_data, options=options).loc[
        periods, series
    ]

    solutions = model.stochsim(
        nrepl,
        input_data,
        simstart,
        simend,
        residstart,
        residend,
        seed=seed,
        options=options,
    )
    successes = [s for s in solutions if isinstance(s, pd.DataFrame)]
    failures = [s for s in solutions if isinstance(s, str)]
    if not successes:
        raise ConvergenceError(
            f"all {nrepl} stochastic replications failed; first: {failures[0]}"
        )

    # (n_success, T, n_series) stack of successful replication paths
    stack = np.stack([s.loc[periods, series].to_numpy(float) for s in successes])
    columns = pd.MultiIndex.from_product([series, quantiles], names=["series", "band"])
    bands = pd.DataFrame(index=periods, columns=columns, dtype=float)
    qs = np.quantile(stack, list(quantiles.values()), axis=0)  # (n_q, T, n_series)
    for qi, label in enumerate(quantiles):
        for si, name in enumerate(series):
            bands[(name, label)] = qs[qi, :, si]

    return StochsimBands(
        bands=bands,
        deterministic=deterministic,
        nrepl=nrepl,
        n_success=len(successes),
        n_failed=len(failures),
        failures=failures,
        seed=seed,
        coverage=tuple(coverage),
        series=tuple(series),
    )
