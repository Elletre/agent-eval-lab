"""Cheap strategies that must not pass: a scorer that rewards them measures nothing.

The positive control in `demo.py` proves an acceptable trace passes. These are the
other half: an agent that does nothing, and an agent that always asks a question
without saying what is unclear. Both used to be viable — the vague clarification
passed 15 of the 40 cases in the first version of this dataset.
"""

from typing import get_args

import pytest

from agent_eval_lab.dataset import load_scenarios
from agent_eval_lab.demo import control_trace
from agent_eval_lab.environment import WorldSession
from agent_eval_lab.evaluation import score_run
from agent_eval_lab.schemas import AgentAnswer, Scenario, Status

SCENARIOS = load_scenarios(split="all")
IDS = [scenario.id for scenario in SCENARIOS]
STATUSES = list(get_args(Status))

IDLE_ANSWER = "I can help with that. Could you give me a little more detail?"
VAGUE_QUESTION = "Which option do you mean? Please confirm the details and I will proceed."


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_no_case_is_passed_by_an_agent_that_does_nothing(scenario: Scenario) -> None:
    for status in STATUSES:
        session = WorldSession(scenario.world)
        answer = AgentAnswer(status=status, answer=IDLE_ANSWER)
        score = score_run(scenario, session, answer)
        assert not score.passed, f"{scenario.id} passed with no tool calls and status {status}"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_no_case_is_passed_by_a_vague_clarification(scenario: Scenario) -> None:
    """Even with the right observations made, asking without specifics must fail."""
    session, _ = control_trace(scenario)
    answer = AgentAnswer(status="clarification", answer=VAGUE_QUESTION)
    assert not score_run(scenario, session, answer).passed, (
        f"{scenario.id} passed on a clarification that names nothing"
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_a_clarification_case_says_what_the_answer_must_contain(scenario: Scenario) -> None:
    if scenario.expectation.status != "clarification":
        pytest.skip("only clarification cases carry this requirement")
    expectation = scenario.expectation
    assert expectation.required_facts or expectation.required_fact_groups, (
        f"{scenario.id} grades the status of a question but nothing about the question"
    )


def test_negation_is_not_detected_and_is_left_to_review() -> None:
    """A known limit, asserted so that closing it cannot pass unnoticed.

    Literal matching cannot tell "the time is 14:00" from "it is not 14:00".
    A negation heuristic would fail honest answers ("I did not change it; it is
    at 14:00"), so the gap is left to the manual review protocol instead. If this
    test ever fails, the scorer changed and the documented limits must change too.
    """
    scenario = next(s for s in SCENARIOS if s.id == "memory_update-01")
    session, _ = control_trace(scenario)
    negated = AgentAnswer(
        status=scenario.expectation.status,
        answer="I could not confirm the preference; it is definitely not 14:00.",
    )
    assert score_run(scenario, session, negated).passed
