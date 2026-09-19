"""Exercise the real Inspect loop with scripted model outputs, without API keys."""

import asyncio
import json
from pathlib import Path

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ChatMessage, ChatMessageTool, ModelOutput

from agent_eval_lab import inspect_task
from agent_eval_lab.schemas import Scenario


def _scenario(sample_id: str, time: str) -> Scenario:
    data = {"family": "authorized_update", "split": "dev", "world": {}}
    data["id"] = sample_id
    data["request"] = f"Set event shared time to {time}; keep its other fields unchanged."
    data["world"]["events"] = [
        {
            "id": "shared",
            "title": f"PRIVATE_TITLE_{sample_id}",
            "date": "2026-01-20",
            "time": "10:00",
            "attendees": [],
        }
    ]
    data["expectation"] = {
        "status": "updated",
        "event_updates": [{"event_id": "shared", "changes": {"time": time}}],
        "required_facts": [time],
        "forbidden_facts": ["ORACLE_SENTINEL"],
        "required_tools": ["update_event"],
        "max_tool_calls": 2,
    }
    return Scenario.model_validate(data)


def test_real_tool_loop_isolates_concurrent_samples_and_hides_oracle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenarios = [_scenario("one", "11:00"), _scenario("two", "15:00")]
    monkeypatch.setattr(inspect_task, "load_scenarios", lambda *args, **kwargs: scenarios)
    first_calls: list[str] = []

    async def respond(messages: list[ChatMessage], *args: object) -> ModelOutput:
        request = next(message.text for message in messages if message.role == "user")
        time = "11:00" if "11:00" in request else "15:00"
        assert "ORACLE_SENTINEL" not in json.dumps([m.model_dump() for m in messages])
        if not any(isinstance(message, ChatMessageTool) for message in messages):
            assert "PRIVATE_TITLE" not in json.dumps([m.model_dump() for m in messages])
            first_calls.append(time)
            # Force overlapping samples rather than merely checking sequential runs.
            await asyncio.sleep(0.02)
            return ModelOutput.for_tool_call(
                "mockllm", "update_event", {"event_id": "shared", "time": time}
            )
        return ModelOutput.from_content(
            "mockllm", json.dumps({"status": "updated", "answer": time, "evidence": [time]})
        )

    task = inspect_task.assistant_eval()
    assert all(sample.target == "" for sample in task.dataset)
    assert all(set(sample.metadata or {}) == {"family"} for sample in task.dataset)
    logs = inspect_eval(
        task,
        model="mockllm/model",
        model_args={"custom_outputs": respond},
        max_samples=2,
        display="none",
        log_dir=str(tmp_path),
    )
    assert logs[0].status == "success", logs[0].error
    assert set(first_calls) == {"11:00", "15:00"}
    assert len(logs[0].samples or []) == 2
    for sample in logs[0].samples or []:
        assert sample.error is None
        score = sample.scores["deterministic_checks"]
        assert score.value == 1, score.explanation
        event = score.metadata["world"]["events"][0]
        assert event["title"] == f"PRIVATE_TITLE_{sample.id}"
        assert event["time"] == ("11:00" if sample.id == "one" else "15:00")
        assert score.metadata["tool_calls"] == 1
    assert all(s.world.events[0].time == "10:00" for s in scenarios)


def test_malformed_final_answer_fails_without_crashing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        inspect_task, "load_scenarios", lambda *args, **kwargs: [_scenario("bad", "11:00")]
    )
    log = inspect_eval(
        inspect_task.assistant_eval(),
        model="mockllm/model",
        display="none",
        log_dir=str(tmp_path),
    )[0]
    assert log.status == "success"
    assert log.samples[0].scores["deterministic_checks"].value == 0


def test_nonterminating_agent_stops_at_turn_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        inspect_task, "load_scenarios", lambda *args, **kwargs: [_scenario("loop", "11:00")]
    )

    def respond(*args: object) -> ModelOutput:
        return ModelOutput.for_tool_call("mockllm", "list_events", {"query": ""})

    log = inspect_eval(
        inspect_task.assistant_eval(),
        model="mockllm/model",
        model_args={"custom_outputs": respond},
        turn_limit=2,
        display="none",
        log_dir=str(tmp_path),
    )[0]
    assert log.status == "success", log.error
    assert log.samples[0].scores["deterministic_checks"].value == 0
    assert log.samples[0].scores["deterministic_checks"].metadata["tool_calls"] <= 2


@pytest.mark.parametrize("kwargs", [{"variant": "unknown"}, {"split": "all"}])
def test_invalid_task_configuration_is_rejected(kwargs: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        inspect_task.assistant_eval(**kwargs)


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [("nonexistent_tool", {}), ("update_event", {"bad": "value"})],
)
def test_framework_rejections_recorded_once_with_correct_state_and_export_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tool_name: str, arguments: dict
) -> None:
    from agent_eval_lab.inspect_export import export_log

    scenario = _scenario("rejections", "11:00")
    monkeypatch.setattr(inspect_task, "load_scenarios", lambda *args, **kwargs: [scenario])

    def respond(messages: list[ChatMessage], *args: object) -> ModelOutput:
        calls = sum(isinstance(message, ChatMessageTool) for message in messages)
        if calls == 0:
            return ModelOutput.for_tool_call(
                tool_name="update_event",
                model="mockllm",
                tool_arguments={"event_id": "shared", "time": "11:00", "title": None},
            )
        if calls == 1:
            return ModelOutput.for_tool_call("mockllm", tool_name, arguments)
        return ModelOutput.from_content(
            "mockllm", json.dumps({"status": "updated", "answer": "11:00", "evidence": []})
        )

    log = inspect_eval(
        inspect_task.assistant_eval(),
        model="mockllm/model",
        model_args={"custom_outputs": respond},
        display="none",
        log_dir=str(tmp_path),
    )[0]
    assert log.status == "success", log.error
    row = export_log(Path(log.location))["results"][0]
    assert row["tool_calls"] == 2
    assert row["tool_errors"] == 1
    assert row["trace"][0]["result"]["ok"] is True
    rejection = row["trace"][1]
    assert rejection["result"]["framework_rejected"] is True
    assert rejection["before"] == rejection["after"] == row["final_world"]
    assert rejection["before"]["events"][0]["time"] == "11:00"
