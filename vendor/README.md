# vendor/ — upstream FRB/US materials (unmodified)

Raw materials published by the Federal Reserve Board, in the public domain
(see `pyfrbus_package/LICENSE`). Downloaded **2026-07-17** from
https://www.federalreserve.gov/econres/us-models-package.htm

- `pyfrbus_package/` — the Fed's official Python implementation of FRB/US,
  version 1.0.0, files dated 2022-04-06 (source in `pyfrbus/`, demos in
  `demos/`, HTML docs in `docs/`, and the full model equation system in
  `models/model.xml`). Used as the authoritative reference for semantics and as
  ground truth for cross-validation. The Board also ships a newer pyfrbus 1.1.1
  (2026-02-05) whose `model.xml` is byte-identical to this one; `VALIDATION.md`
  §2b records a cross-check against that release.
- `data_only_package/` — October 2026 data vintage (Board page "Updated:
  October 13, 2026"; archive members dated 2026-10-06; downloaded
  **2026-11-16**). `LONGBASE.TXT` is history through 2026Q2 plus the long-run
  projection baseline from 2026Q3; `HISTDATA.TXT` is the history alone. It
  replaces the April 2026 vintage (LONGBASE sha256 `6f2cc04e…`).
- `frbus_package/documentation/` — model documentation (PDF/HTML), including
  published simulation properties of the model.
- `*.zip` — the original downloaded archives.

Nothing in this directory is modified by this repository. The cross-validation
environment (see `VALIDATION.md`) patches a **copy** of `pyfrbus_package`
outside the repo to run on modern dependencies.

Vintage note, re-checked **2026-11-16**: the Board's data page reads
"Updated: October 13, 2026" and the archive differs from the April 2026 one
(new SHA-256 in `manifest.json`), so it was adopted. The EViews model package
is still dated April 21, 2022, and the pyfrbus served today (1.1.1, files dated
2026-02-05) has a `models/model.xml` byte-identical to the vendored 1.0.0 one,
so the model itself is unchanged. (On 2026-07-18 the page's "May 5, 2026" label
had served an archive byte-identical to the April one.)
