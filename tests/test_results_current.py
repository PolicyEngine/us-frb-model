"""The currentness check for the long-solve results (scripts/check_results_current.py).

The re-solve itself runs in the ``long-solve-currentness`` CI job, one target
per matrix entry. Here, fast and with no solve: the comparison is shown to
fail on a stale file, and every results/*.json is shown to have a check.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import check_results_current as crc  # noqa: E402

RESULTS = REPO / "results"


def test_every_results_json_has_a_currentness_check():
    covered = {f for _, _, files in crc.TARGETS.values() for f in files if f.endswith(".json")}
    assert not covered & set(crc.COVERED_ELSEWHERE)
    on_disk = {p.name for p in RESULTS.glob("*.json")}
    assert on_disk == covered | set(crc.COVERED_ELSEWHERE)
    for test_file in crc.COVERED_ELSEWHERE.values():
        assert (REPO / test_file).exists(), test_file


def test_ci_runs_every_target():
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    job = ci.split("long-solve-currentness:")[1].split("\n  # ")[0]
    for target in crc.TARGETS:
        assert f"- {target}\n" in job, target


@pytest.mark.parametrize("target", list(crc.TARGETS))
def test_committed_files_equal_themselves(target):
    assert crc.compare_dirs(target, RESULTS) == []


def _stale_copy(tmp_path, target, edit):
    for name in crc.TARGETS[target][2]:
        (tmp_path / name).write_text((RESULTS / name).read_text())
    path = tmp_path / crc.TARGETS[target][2][0]
    doc = json.loads(path.read_text())
    edit(doc)
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return crc.compare_dirs(target, tmp_path)


def test_a_moved_number_is_reported(tmp_path):
    def edit(doc):
        doc["rows"]["start_2020"]["core_trough"][0] += 2e-6

    problems = _stale_copy(tmp_path, "laforte_vintage_check", edit)
    assert len(problems) == 1 and "start_2020.core_trough[0]" in problems[0]


def test_a_move_inside_the_tolerance_is_not(tmp_path):
    def edit(doc):
        doc["rows"]["start_2020"]["core_trough"][0] += 1e-9

    assert _stale_copy(tmp_path, "laforte_vintage_check", edit) == []


def test_a_missing_or_extra_key_is_reported(tmp_path):
    def drop(doc):
        del doc["rows"]["start_2020"]

    assert any("only in" in p for p in _stale_copy(tmp_path, "laforte_vintage_check", drop))

    def add(doc):
        doc["scenarios"]["monetary"]["2027Q1"] = {}

    assert any("only in" in p for p in _stale_copy(tmp_path, "window_2026q3_preview", add))


def test_a_shorter_list_a_changed_label_and_a_stale_render_are_reported(tmp_path):
    def shorten(doc):
        doc.pop()

    problems = _stale_copy(tmp_path, "expectations_matched_closures", shorten)
    assert any("length" in p for p in problems)

    def relabel(doc):
        doc["label"] = "validated"

    assert _stale_copy(tmp_path, "window_2026q3_preview", relabel)

    target = "window_2026q3_preview"
    for name in crc.TARGETS[target][2]:
        (tmp_path / name).write_text((RESULTS / name).read_text())
    md = tmp_path / "window_2026q3_preview.md"
    md.write_text(md.read_text().replace("-0.5", "-0.6", 1))
    assert crc.compare_dirs(target, tmp_path) == [
        "window_2026q3_preview.md: rendered text differs from a fresh render"
    ]


def test_diff_json_is_strict_about_types_and_nan():
    assert crc.diff_json({"a": 1.0}, {"a": 1}) == []
    assert crc.diff_json({"a": True}, {"a": 1})
    assert crc.diff_json({"a": "1"}, {"a": 1})
    assert crc.diff_json({"a": float("nan")}, {"a": float("nan")})
    doc = {"a": [1, {"b": 2.5}], "c": None}
    assert crc.diff_json(doc, copy.deepcopy(doc)) == []
