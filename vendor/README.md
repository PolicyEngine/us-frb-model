# vendor/ — upstream FRB/US materials (unmodified)

Raw materials published by the Federal Reserve Board, in the public domain
(see `pyfrbus_package/LICENSE`). Downloaded **2026-07-17** from
https://www.federalreserve.gov/econres/us-models-package.htm

- `pyfrbus_package/` — the Fed's official Python implementation of FRB/US
  (source in `pyfrbus/`, demos in `demos/`, HTML docs in `docs/`, and the full
  model equation system in `models/model.xml`). Used as the authoritative
  reference for semantics and as ground truth for cross-validation.
- `data_only_package/LONGBASE.TXT` — April 2026 data vintage: history plus the
  long-run projection baseline.
- `frbus_package/documentation/` — model documentation (PDF/HTML), including
  published simulation properties of the model.
- `*.zip` — the original downloaded archives.

Nothing in this directory is modified by this repository. The cross-validation
environment (see `VALIDATION.md`) patches a **copy** of `pyfrbus_package`
outside the repo to run on modern dependencies.
