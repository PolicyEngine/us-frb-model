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
- `data_only_package/LONGBASE.TXT` — April 2026 data vintage: history plus the
  long-run projection baseline.
- `frbus_package/documentation/` — model documentation (PDF/HTML), including
  published simulation properties of the model.
- `*.zip` — the original downloaded archives.

Nothing in this directory is modified by this repository. The cross-validation
environment (see `VALIDATION.md`) patches a **copy** of `pyfrbus_package`
outside the repo to run on modern dependencies.

Vintage note, re-checked **2026-07-18**: the Board's package page labels the
data download "Updated: May 5, 2026", but the archive served from that link is
byte-identical to the one vendored here — same SHA-256, all members stamped
2026-04-08. There is no newer data vintage to adopt despite the page label.
