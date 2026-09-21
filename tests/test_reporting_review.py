"""Review regressions: malformed artifacts must not produce confident reports."""

from copy import deepcopy

import pytest

from agent_eval_lab.dataset import load_scenarios
from agent_eval_lab.demo import demo_run
from agent_eval_lab.reporting import compare_runs, report_markdown, validate_run


@pytest.fixture
def run():
    return demo_run(load_scenarios(split="dev")[:1], "control")


@pytest.mark.parametrize("value", ["false", 1, [], None])
def test_report_rejects_nonboolean_gate_values(run, value):
    row = run["results"][0]
    row["checks"]["required_facts"] = value
    row["passed"] = all(row["checks"].values())
    row["failures"] = [] if row["passed"] else ["required_facts"]
    with pytest.raises(ValueError):
        report_markdown(run)


@pytest.mark.parametrize("failures", [[], ["unrelated_gate"], ["required_facts", "required_facts"]])
def test_report_rejects_failure_list_disagreeing_with_gates(run, failures):
    row = run["results"][0]
    row["checks"]["required_facts"] = False
    row["passed"] = False
    row["failures"] = failures
    with pytest.raises(ValueError):
        validate_run(run)


@pytest.mark.parametrize(
    "key", ["dataset_hash", "source_hash", "scorer_version", "environment_version"]
)
def test_comparison_rejects_missing_critical_identity_on_both_sides(run, key):
    left, right = deepcopy(run), deepcopy(run)
    left["provenance"].pop(key, None)
    right["provenance"].pop(key, None)
    with pytest.raises(ValueError):
        compare_runs(left, right)


def test_comparison_rejects_model_runs_without_model_identity(run):
    left, right = deepcopy(run), deepcopy(run)
    for item in (left, right):
        item["kind"] = "model"
        item["provenance"].pop("model", None)
    with pytest.raises(ValueError):
        compare_runs(left, right)


def test_real_regression_is_reported_without_inflating_scenarios(run):
    left, right = deepcopy(run), deepcopy(run)
    right["results"][0]["checks"]["required_facts"] = False
    right["results"][0]["passed"] = False
    right["results"][0]["failures"] = ["required_facts"]
    comparison = compare_runs(left, right)
    assert "pass → fail: 1" in comparison
    assert "1 down" in comparison, "a scenario that lost its only trial must be reported as moved"
    assert "sign test" in comparison, "a comparison without uncertainty invites over-reading"
    assert "NOT LLM results" in comparison
