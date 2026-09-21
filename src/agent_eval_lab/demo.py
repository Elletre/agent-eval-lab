"""Oracle-driven control traces: test the harness, never measure agent intelligence.

These fixtures deliberately read expectations. They are not an agent or LLM proxy.
"""

from datetime import UTC, datetime
from typing import Any

from agent_eval_lab.dataset import dataset_hash
from agent_eval_lab.environment import WorldSession
from agent_eval_lab.evaluation import score_run
from agent_eval_lab.provenance import provenance
from agent_eval_lab.schemas import AgentAnswer, Scenario


def control_trace(scenario: Scenario) -> tuple[WorldSession, AgentAnswer]:
    session = WorldSession(scenario.world)
    expected = scenario.expectation
    for name in expected.required_tools:
        requirements = [item for item in expected.required_observations if item.tool == name]
        if requirements:
            arguments = dict(requirements[0].arguments)
        elif name == "list_events":
            arguments = {"query": ""}
        elif name == "lookup_memory":
            arguments = {
                "key": scenario.world.memories[0].key
                if scenario.world.memories
                else "preferred_meeting_time"
            }
        elif name == "read_email":
            arguments = {
                "email_id": scenario.world.emails[0].id if scenario.world.emails else "missing"
            }
        else:
            permissions = expected.event_updates + expected.allowed_write_attempts
            if not permissions:
                raise ValueError(f"{scenario.id}: update fixture needs an explicit permission")
            update = permissions[0]
            arguments = {"event_id": update.event_id, **update.changes}
        if name == "list_events":
            arguments.setdefault("query", "")
        # An observation requirement may specify only a subset of an update.
        if name == "update_event":
            update = (expected.event_updates + expected.allowed_write_attempts)[0]
            arguments = {"event_id": update.event_id, **update.changes} | arguments
        session.call(name, arguments)
    facts = list(expected.required_facts) + [group[0] for group in expected.required_fact_groups]
    answer = AgentAnswer(
        status=expected.status,
        answer=" ".join(facts)
        or {
            "clarification": "Please clarify the missing or conflicting information.",
            "blocked": "The requested operation was blocked by a tool error.",
        }.get(expected.status, "Completed."),
    )
    return session, answer


def demo_run(scenarios: list[Scenario], variant: str, repeats: int = 1) -> dict[str, Any]:
    if variant not in {"control", "faults"}:
        raise ValueError("demo variant must be control or faults")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    rows = []
    for scenario in scenarios:
        for trial in range(1, repeats + 1):
            session, control_answer = control_trace(scenario)
            answer: AgentAnswer | None = control_answer
            if variant == "faults":
                # One deliberately corrupted outcome per case, independent of split.
                if scenario.expectation.status == "updated":
                    session.state = scenario.world.model_copy(deep=True)
                elif scenario.world.events:
                    event = scenario.world.events[0]
                    session.call("update_event", {"event_id": event.id, "title": "UNAUTHORIZED"})
                else:
                    answer = None
            score = score_run(scenario, session, answer)
            rows.append(
                {
                    "scenario_id": scenario.id,
                    "family": scenario.family,
                    "trial": trial,
                    "passed": score.passed,
                    "checks": score.checks,
                    "failures": score.failures,
                    "tool_calls": len(session.trace),
                    "tool_errors": sum(call.result.get("ok") is False for call in session.trace),
                    "answer": answer.model_dump() if answer else None,
                    "trace": [call.model_dump() for call in session.trace],
                    "final_world": session.state.model_dump(),
                    "usage": {},
                    "elapsed_seconds": None,
                    "error": None,
                }
            )
    splits = {scenario.split for scenario in scenarios}
    return {
        "schema_version": 1,
        "kind": "scripted_fixture",
        "variant": variant,
        "split": next(iter(splits)) if len(splits) == 1 else "all",
        "created_at": datetime.now(UTC).isoformat(),
        "provenance": provenance()
        | {"dataset_hash": dataset_hash(scenarios), "model": None, "generation_config": {}},
        "results": rows,
    }
