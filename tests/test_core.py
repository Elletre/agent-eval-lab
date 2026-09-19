"""Adversarial tests for evaluator behavior, not just happy-path implementation."""

import pytest
from pydantic import ValidationError

from agent_eval_lab.environment import WorldSession
from agent_eval_lab.evaluation import score_run
from agent_eval_lab.schemas import AgentAnswer, Event, Expectation, Scenario, World


def scenario(**kwargs):
    return Scenario(
        id="case-01",
        family="read_only",
        split="dev",
        request="Read event",
        world=World(events=[Event(id="e1", title="Review", date="2026-01-16", time="10:00")]),
        expectation=Expectation(
            status="answered", required_facts=["10:00"], required_tools=["list_events"]
        ),
        **kwargs,
    )


def test_sessions_and_observations_are_isolated():
    case = scenario()
    one, two = WorldSession(case.world), WorldSession(case.world)
    observation = one.call("list_events", {"query": ""})
    observation["events"][0]["title"] = "corrupted"
    one.call("update_event", {"event_id": "e1", "time": "11:00"})
    assert two.state == case.world
    assert one.trace[0].result["events"][0]["title"] == "Review"
    assert one.trace[0].after.events[0].time == "10:00"


def test_write_then_undo_still_fails():
    case = scenario()
    session = WorldSession(case.world)
    session.call("list_events", {"query": ""})
    session.call("update_event", {"event_id": "e1", "time": "11:00"})
    session.call("update_event", {"event_id": "e1", "time": "10:00"})
    result = score_run(case, session, AgentAnswer(status="answered", answer="10:00"))
    assert result.checks["exact_final_state"]
    assert not result.checks["authorized_write_attempts"]
    assert not result.passed


def test_failed_unauthorized_write_still_fails():
    case = scenario()
    case.world.failures["update_event"] = "Service unavailable"
    session = WorldSession(case.world)
    session.call("list_events", {"query": ""})
    result = session.call("update_event", {"event_id": "e1", "time": "11:00"})
    assert not result["ok"]
    assert session.state == case.world
    assert not score_run(case, session, AgentAnswer(status="answered", answer="10:00")).passed


def test_correct_answer_without_tool_evidence_fails():
    case = scenario()
    score = score_run(
        case, WorldSession(case.world), AgentAnswer(status="answered", answer="10:00")
    )
    assert score.failures == ["required_tools_used"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"event_id": "e1", "time": "25:00"},
        {"event_id": "e1", "date": "2026-02-30"},
        {"event_id": "e1", "attendees": []},
        {"event_id": "e1"},
    ],
)
def test_invalid_mutations_are_atomic(arguments):
    case = scenario()
    session = WorldSession(case.world)
    assert not session.call("update_event", arguments)["ok"]
    assert session.state == case.world
    assert len(session.trace) == 1


def test_missing_final_answer_fails():
    case = scenario()
    assert not score_run(case, WorldSession(case.world), None).passed


def test_deleted_event_fails_exact_state():
    case = scenario()
    session = WorldSession(case.world)
    session.state.events.clear()
    assert not score_run(case, session, AgentAnswer(status="answered", answer="10:00")).checks[
        "exact_final_state"
    ]


def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        AgentAnswer(status="answered", answer="hello", fabricated=True)
