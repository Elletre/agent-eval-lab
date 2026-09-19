"""Native-log exports preserve failures and reject incomplete evidence."""

import json
from pathlib import Path

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

from agent_eval_lab.inspect_export import export_log
from agent_eval_lab.inspect_task import assistant_eval


@pytest.fixture(scope="module")
def completed_log(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("native_inspect")
    log = inspect_eval(
        assistant_eval(),
        model="mockllm/model",
        limit=1,
        epochs=2,
        display="none",
        log_dir=str(directory),
    )[0]
    assert log.status == "success", log.error
    return Path(log.location)


def _modified(log: EvalLog, tmp_path: Path) -> Path:
    path = tmp_path / "modified.json"
    write_eval_log(log, str(path))
    return path


def test_actual_mock_log_export_preserves_trials_failures_and_provenance(
    completed_log: Path,
) -> None:
    exported = export_log(completed_log)
    assert exported["kind"] == "mock_model"
    assert exported["schema_version"] == 1
    assert exported["provenance"]["model"] == "mockllm/model"
    assert len(exported["provenance"]["source_log_sha256"]) == 64
    assert len(exported["provenance"]["dataset_hash"]) == 64
    assert len(exported["results"]) == 2
    assert {row["trial"] for row in exported["results"]} == {1, 2}
    assert all(row["passed"] is False for row in exported["results"])
    assert all(row["answer"] is None for row in exported["results"])
    assert all(row["failures"] for row in exported["results"])
    assert all(row["usage"] for row in exported["results"])
    json.dumps(exported, allow_nan=False)


@pytest.mark.parametrize("status", ["started", "cancelled", "error"])
def test_unfinished_status_rejected(completed_log: Path, tmp_path: Path, status: str) -> None:
    log = read_eval_log(str(completed_log))
    log.status = status
    with pytest.raises(ValueError, match="Only successful"):
        export_log(_modified(log, tmp_path))


@pytest.mark.parametrize("damage", ["missing", "duplicate", "unscored", "completion", "checks"])
def test_incomplete_or_inconsistent_samples_rejected(
    completed_log: Path, tmp_path: Path, damage: str
) -> None:
    log = read_eval_log(str(completed_log))
    assert log.samples is not None and log.results is not None
    if damage == "missing":
        log.samples.pop()
    elif damage == "duplicate":
        log.samples[1] = log.samples[0].model_copy(deep=True)
    elif damage == "unscored":
        log.samples[0].scores = None
    elif damage == "completion":
        log.results.completed_samples -= 1
    elif damage == "checks":
        log.samples[0].scores["deterministic_checks"].value = 1
    with pytest.raises(ValueError):
        export_log(_modified(log, tmp_path))


def test_effective_generation_config_preserves_task_and_cli_overrides(
    completed_log: Path, tmp_path: Path
) -> None:
    from agent_eval_lab.reporting import compare_runs

    baseline = export_log(completed_log)
    assert baseline["provenance"]["generation_config"]["max_tokens"] == 1024
    assert baseline["provenance"]["generation_config"]["parallel_tool_calls"] is False
    log = inspect_eval(
        assistant_eval(),
        model="mockllm/model",
        limit=1,
        epochs=2,
        max_tokens=256,
        temperature=0.25,
        display="none",
        log_dir=str(tmp_path),
    )[0]
    assert log.status == "success", log.error
    overridden = export_log(Path(log.location))
    config = overridden["provenance"]["generation_config"]
    assert config["max_tokens"] == 256
    assert config["temperature"] == 0.25
    assert config["parallel_tool_calls"] is False
    with pytest.raises(ValueError, match="generation_config differs"):
        compare_runs(baseline, overridden)


def test_model_defaults_survive_when_not_overridden(completed_log: Path, tmp_path: Path) -> None:
    log = read_eval_log(str(completed_log))
    log.eval.model_generate_config.top_p = 0.8
    log.eval.model_generate_config.max_tokens = 9000
    exported = export_log(_modified(log, tmp_path))
    config = exported["provenance"]["generation_config"]
    assert config["top_p"] == 0.8
    assert config["max_tokens"] == 1024
