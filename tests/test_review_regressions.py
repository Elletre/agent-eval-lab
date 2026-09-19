"""Independent review regressions for scorer bypasses and malformed oracle data."""

import json
from pathlib import Path

import pytest
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ChatMessage, ChatMessageTool, ModelOutput
from pydantic import ValidationError

from agent_eval_lab import inspect_task
from agent_eval_lab.environment import WorldSession
from agent_eval_lab.evaluation import score_run
from agent_eval_lab.schemas import AgentAnswer, Scenario


def review_scenario() -> Scenario:
    return Scenario.model_validate(
        {
            "id": "review-01",
            "family": "read_only",
            "split": "dev",
            "request": "Look up preferred_meeting_time; report the value. Do not change anything.",
            "world": {
                "memories": [
                    {
                        "key": "preferred_meeting_time",
                        "value": "10:00",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                ],
                "events": [{"id": "e1", "title": "Review", "date": "2026-01-20", "time": "10:00"}],
            },
            "expectation": {
                "status": "answered",
                "required_facts": ["10:00"],
                "required_tools": ["lookup_memory"],
                "required_observations": [
                    {"tool": "lookup_memory", "arguments": {"key": "preferred_meeting_time"}}
                ],
                "max_tool_calls": 1,
            },
        }
    )


def test_wrong_memory_lookup_cannot_ground_a_lucky_guess() -> None:
    scenario = review_scenario()
    session = WorldSession(scenario.world)
    session.call("lookup_memory", {"key": "nonexistent"})
    score = score_run(scenario, session, AgentAnswer(status="answered", answer="10:00"))
    assert not score.passed
    assert "required_observations" in score.failures


def test_allowed_failed_write_does_not_authorize_a_successful_mutation() -> None:
    scenario = review_scenario()
    raw = scenario.model_dump()
    raw["expectation"]["allowed_write_attempts"] = [
        {"event_id": "e1", "changes": {"time": "11:00"}}
    ]
    raw["expectation"]["max_tool_calls"] = 2
    scenario = Scenario.model_validate(raw)
    session = WorldSession(scenario.world)
    session.call("lookup_memory", {"key": "preferred_meeting_time"})
    session.call("update_event", {"event_id": "e1", "time": "11:00"})
    score = score_run(scenario, session, AgentAnswer(status="answered", answer="10:00"))
    assert score.checks["authorized_write_attempts"]
    assert not score.checks["exact_final_state"]
    assert not score.passed


@pytest.mark.parametrize("bad_name", ["delete_calendar", "lookup_memroy"])
def test_unknown_observation_tool_rejected_during_dataset_validation(bad_name: str) -> None:
    raw = review_scenario().model_dump()
    raw["expectation"]["required_observations"][0]["tool"] = bad_name
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


@pytest.mark.parametrize(
    "attempt",
    [
        {"event_id": "absent", "changes": {"time": "11:00"}},
        {"event_id": "e1", "changes": {"time": "99:00"}},
    ],
)
def test_invalid_allowed_attempt_rejected_during_dataset_validation(attempt: dict) -> None:
    raw = review_scenario().model_dump()
    raw["expectation"]["allowed_write_attempts"] = [attempt]
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [("nonexistent_tool", {}), ("lookup_memory", {"wrong_argument": "x"})],
)
def test_inspect_rejected_tool_calls_count_toward_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tool_name: str, arguments: dict
) -> None:
    scenario = review_scenario()
    monkeypatch.setattr(inspect_task, "load_scenarios", lambda *args, **kwargs: [scenario])

    def respond(messages: list[ChatMessage], *args: object) -> ModelOutput:
        tool_results = [message for message in messages if isinstance(message, ChatMessageTool)]
        if not tool_results:
            return ModelOutput.for_tool_call("mockllm", tool_name, arguments)
        if len(tool_results) == 1:
            return ModelOutput.for_tool_call(
                "mockllm", "lookup_memory", {"key": "preferred_meeting_time"}
            )
        return ModelOutput.from_content(
            "mockllm", json.dumps({"status": "answered", "answer": "10:00", "evidence": []})
        )

    log = inspect_eval(
        inspect_task.assistant_eval(),
        model="mockllm/model",
        model_args={"custom_outputs": respond},
        display="none",
        log_dir=str(tmp_path),
    )[0]
    assert log.status == "success", log.error
    sample = log.samples[0]
    assert sample.error is None
    score = sample.scores["deterministic_checks"]
    # Both rejected and accepted attempts consume the one-call budget.
    assert score.value == 0, score.metadata
    assert score.metadata["tool_calls"] == 2
    assert not score.metadata["checks"]["tool_budget"]
