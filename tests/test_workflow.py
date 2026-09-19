"""End-to-end offline workflows and a fixed benchmark inventory."""

import json
from collections import Counter
from copy import deepcopy

import pytest

from agent_eval_lab.cli import main
from agent_eval_lab.dataset import dataset_hash, load_scenarios
from agent_eval_lab.demo import demo_run
from agent_eval_lab.reporting import compare_runs, summarize


def test_dataset_inventory_and_controls():
    cases = load_scenarios(split="all")
    assert len(cases) == 40
    assert Counter(s.split for s in cases) == {"dev": 24, "test": 16}
    assert set(Counter(s.family for s in cases).values()) == {5}
    good = demo_run(cases, "control")
    assert all(row["passed"] for row in good["results"])
    bad = demo_run(cases, "faults")
    assert all(not row["passed"] for row in bad["results"])


def test_cli_creates_parseable_trace_and_report(tmp_path):
    output = tmp_path / "control.json"
    assert main(["demo", "--repeats", "2", "--output", str(output)]) == 0
    run = json.loads(output.read_text())
    stats = summarize(run)
    assert stats["scenarios"] == 24
    assert stats["trials"] == 48
    assert stats["stable_pass_scenarios"] == 24
    assert "NOT model performance" in output.with_suffix(".md").read_text()
    assert "source_hash" in run["provenance"]


def test_comparison_rejects_changed_dataset_and_unpaired_trials():
    run = demo_run(load_scenarios()[:2], "control")
    different = deepcopy(run)
    different["provenance"]["dataset_hash"] = "changed"
    with pytest.raises(ValueError, match="dataset_hash"):
        compare_runs(run, different)
    different = deepcopy(run)
    different["results"].pop()
    with pytest.raises(ValueError, match="pairs"):
        compare_runs(run, different)


def test_fingerprint_detects_semantic_dataset_change():
    cases = load_scenarios()
    before = dataset_hash(cases)
    cases[0].request += " Please."
    assert dataset_hash(cases) != before


def test_cli_negative_repeats_fails_without_creating_output(tmp_path):
    output = tmp_path / "bad.json"
    with pytest.raises(SystemExit) as exc:
        main(["demo", "--repeats", "0", "--output", str(output)])
    assert exc.value.code == 2
    assert not output.exists()
