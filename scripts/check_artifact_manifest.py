"""Verify that model and data artifacts match their independent manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest() -> dict[str, str]:
    manifest = json.loads((VENDOR / "manifest.json").read_text())
    targets = {
        "model_package": (
            VENDOR / manifest["model_package"]["artifact"],
            manifest["model_package"]["sha256"],
        ),
        "model_xml": (
            VENDOR / "pyfrbus_package/models/model.xml",
            manifest["model_package"]["model_xml_sha256"],
        ),
        "data_package": (
            VENDOR / manifest["data_package"]["artifact"],
            manifest["data_package"]["sha256"],
        ),
        "longbase": (
            VENDOR / "data_only_package/LONGBASE.TXT",
            manifest["data_package"]["longbase_sha256"],
        ),
    }
    observed = {name: sha256(path) for name, (path, _) in targets.items()}
    mismatches = {
        name: {"expected": expected, "observed": observed[name]}
        for name, (_, expected) in targets.items()
        if observed[name] != expected
    }
    if mismatches:
        raise RuntimeError(f"FRB/US artifact provenance mismatch: {mismatches}")
    return observed


if __name__ == "__main__":
    for name, digest in verify_manifest().items():
        print(f"{name}: {digest}")
