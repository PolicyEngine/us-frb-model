"""Are the committed long-solve results what the code and data produce today?

Several files in results/ come from long stacked (MCE) solves that the fast
suite does not re-run. This script regenerates each one into a scratch
directory with its own generating script and compares it with the committed
copy: JSON structure exactly, floats to 1e-6 (the tolerance of the other
"committed file is current" gates), and the rendered markdown as text. A
committed file left behind by a change to the solver, the model file, the
LONGBASE vintage or the generating script fails here.

It compares; it never writes into results/. To refresh a stale file, run the
generating script (in CI: download the ``fresh-<target>`` artifact of the
``long-solve-currentness`` job) and commit its output.

    uv run python scripts/check_results_current.py [TARGET ...] [--keep DIR]
    uv run python scripts/check_results_current.py TARGET --fresh DIR [--committed DIR]

With ``--fresh`` nothing is solved: the files in DIR are compared with the
committed ones (or with ``--committed DIR``). The MCE targets are heavy; take
the heavy-job lock or let CI run them.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
TOL = 1e-6

# target -> (generating module in scripts/, extra argv, files it writes)
TARGETS: dict[str, tuple[str, list[str], tuple[str, ...]]] = {
    "expectations_comparison": (
        "expectations_comparison",
        [],
        ("expectations_comparison.json", "expectations_comparison.md"),
    ),
    "expectations_matched_closures": (
        "expectations_comparison",
        ["--matched"],
        ("expectations_matched_closures.json", "expectations_matched_closures.md"),
    ),
    "laforte_vintage_check": ("laforte_vintage_check", [], ("laforte_vintage_check.json",)),
    "episode_2022_tightening_mce_mcap": (
        "episode_2022_tightening",
        ["--mce", "mcap"],
        ("episode_2022_tightening_mce_mcap.json", "episode_2022_tightening_mce_mcap.md"),
    ),
    "episode_2022_tightening_mce_mcap_wp": (
        "episode_2022_tightening",
        ["--mce", "mcap+wp"],
        ("episode_2022_tightening_mce_mcap_wp.json", "episode_2022_tightening_mce_mcap_wp.md"),
    ),
    "window_2026q3_preview": (
        "window_2026q3_preview",
        [],
        ("window_2026q3_preview.json", "window_2026q3_preview.md"),
    ),
}

# Every other results/*.json and the test that already re-solves it. The fast
# suite checks that this list and TARGETS together cover results/ exactly, so
# a new results file cannot be added without a currentness check.
COVERED_ELSEWHERE = {
    "benchmark_multipliers.json": "tests/test_benchmarks.py",
    "episode_2022_tightening.json": "tests/test_benchmarks.py",
    "inflation_transmission.json": "tests/test_inflation_transmission.py",
    "scenario_sweep.json": "tests/test_scenario_sweep.py",
    "site_numbers.json": "tests/test_site_numbers.py",
    "site_responses.json": "tests/test_site_responses.py",
}


def diff_json(committed, fresh, tol: float = TOL, path: str = "$") -> list[str]:
    """Differences between two parsed JSON documents; empty when current."""
    if isinstance(committed, dict) and isinstance(fresh, dict):
        out = [f"{path}.{k}: only in committed" for k in committed.keys() - fresh.keys()]
        out += [f"{path}.{k}: only in fresh" for k in fresh.keys() - committed.keys()]
        for k in committed.keys() & fresh.keys():
            out += diff_json(committed[k], fresh[k], tol, f"{path}.{k}")
        return sorted(out)
    if isinstance(committed, list) and isinstance(fresh, list):
        if len(committed) != len(fresh):
            return [f"{path}: length {len(committed)} committed, {len(fresh)} fresh"]
        out = []
        for n, (a, b) in enumerate(zip(committed, fresh, strict=True)):
            out += diff_json(a, b, tol, f"{path}[{n}]")
        return out
    num = (int, float)
    if (
        isinstance(committed, num)
        and isinstance(fresh, num)
        and not isinstance(committed, bool)
        and not isinstance(fresh, bool)
    ):
        # NaN never equals anything, so it is reported.
        if not abs(committed - fresh) <= tol:
            return [f"{path}: {committed!r} committed, {fresh!r} fresh"]
        return []
    if type(committed) is not type(fresh) or committed != fresh:
        return [f"{path}: {committed!r} committed, {fresh!r} fresh"]
    return []


def compare_dirs(target: str, fresh_dir: Path, committed_dir: Path = RESULTS) -> list[str]:
    """Compare the files of one target in two directories."""
    problems = []
    for name in TARGETS[target][2]:
        c, f = committed_dir / name, fresh_dir / name
        if not c.exists() or not f.exists():
            problems.append(f"{name}: missing ({'committed' if not c.exists() else 'fresh'})")
        elif name.endswith(".json"):
            diffs = diff_json(json.loads(c.read_text()), json.loads(f.read_text()))
            problems += [f"{name} {d}" for d in diffs]
        elif c.read_text() != f.read_text():
            problems.append(f"{name}: rendered text differs from a fresh render")
    return problems


def regenerate(target: str, out: Path) -> None:
    module, argv, _ = TARGETS[target]
    sys.path.insert(0, str(REPO / "scripts"))
    rc = importlib.import_module(module).main([*argv, "--out", str(out)])
    if rc:
        raise RuntimeError(f"{module} exited {rc}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("targets", nargs="*", default=list(TARGETS), metavar="TARGET")
    p.add_argument("--keep", type=Path, help="write the fresh files here (default: a temp dir)")
    p.add_argument("--fresh", type=Path, help="compare these files instead of solving")
    p.add_argument("--committed", type=Path, default=RESULTS)
    args = p.parse_args(argv)
    unknown = [t for t in args.targets if t not in TARGETS]
    if unknown:
        p.error(f"unknown target(s) {unknown}; choose from {list(TARGETS)}")
    failed = False
    for target in args.targets:
        if args.fresh:
            fresh_dir = args.fresh
        else:
            fresh_dir = args.keep or Path(tempfile.mkdtemp(prefix="frbus_current_"))
            regenerate(target, fresh_dir)
        problems = compare_dirs(target, fresh_dir, args.committed)
        if problems:
            failed = True
            print(f"STALE {target}: {len(problems)} difference(s) from a fresh solve")
            for line in problems[:40]:
                print(f"  {line}")
            if len(problems) > 40:
                print(f"  ... and {len(problems) - 40} more")
        else:
            print(f"current {target}: committed files equal a fresh solve (floats to {TOL:g})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
