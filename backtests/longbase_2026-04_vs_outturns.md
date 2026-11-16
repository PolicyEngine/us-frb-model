# LONGBASE vs outturns: April 2026 vintage (frozen record)

Frozen on 16 Nov 2026, when the repo moved to the October 2026 LONGBASE. The April 2026 vintage is no longer vendored, so `scripts/backtest_longbase.py` no longer regenerates this file. Under the October vintage, 2026Q1 and 2026Q2 are history, so the live report (`longbase_vs_outturns.md`) scores that vintage's first projected quarter instead.

LONGBASE.TXT, April 2026 near-term path against realized FRED data (2026Q1, 2026Q2). Error = LONGBASE − outturn. This is a report on the Fed's baseline, not a gate.

| quarter | variable | concept | LONGBASE | outturn | error |
|---|---|---|---|---|---|
| 2026Q1 | xgdp (GDPC1) | real GDP growth (annualized q/q %) | 2.42 | 2.09 | +0.33 |
| 2026Q2 | xgdp (GDPC1) | real GDP growth (annualized q/q %) | 2.41 | 1.50 | +0.91 |
| 2026Q1 | lur (UNRATE) | unemployment rate (%, quarterly avg) | 4.46 | 4.33 | +0.12 |
| 2026Q2 | lur (UNRATE) | unemployment rate (%, quarterly avg) | 4.44 | 4.27 | +0.17 |
| 2026Q1 | pcxfe (PCEPILFE) | core PCE inflation (annualized compounded q/q % of pcxfe) | 2.77 | 4.42 | -1.65 |
| 2026Q2 | pcxfe (PCEPILFE) | core PCE inflation (annualized compounded q/q % of pcxfe) | 2.76 | 3.42 | -0.65 |
| 2026Q1 | rff (FEDFUNDS) | federal funds rate (%, quarterly avg) | 3.79 | 3.64 | +0.14 |
| 2026Q2 | rff (FEDFUNDS) | federal funds rate (%, quarterly avg) | 3.67 | 3.63 | +0.04 |
