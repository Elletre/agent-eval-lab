"""Committed run artifacts must stay valid, self-consistent and honestly labelled."""

import json
from pathlib import Path

import pytest

from agent_eval_lab.reporting import report_markdown, summarize, validate_run

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = sorted(ROOT.glob("reports/*.json")) + sorted(ROOT.glob("experiments/**/*.json"))


@pytest.mark.parametrize("path", ARTIFACTS, ids=[str(p.relative_to(ROOT)) for p in ARTIFACTS])
def test_a_committed_run_still_validates_and_renders(path: Path) -> None:
    run = json.loads(path.read_text())
    validate_run(run)
    summary = summarize(run)
    assert summary["trials"] >= summary["scenarios"] >= 1
    report = report_markdown(run)
    if run["kind"] != "model":
        assert "NOT model performance" in report, "a harness control must say so in its report"
    assert run["provenance"]["scorer_version"], "a run without a scorer version cannot be placed"
