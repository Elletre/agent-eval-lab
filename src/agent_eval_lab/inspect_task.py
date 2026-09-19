"""Inspect AI adapter: real model/tool execution over the deterministic core.

Oracle data lives in harness closures. Only the request, prompt and tool responses
are sent to the model. Each sample owns a fresh world and a sample-local store.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    GenerateConfig,
)
from inspect_ai.scorer import Score, Scorer, Target, accuracy, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool, tool
from inspect_ai.util import store
from pydantic import ValidationError

from agent_eval_lab.dataset import dataset_hash, load_scenarios
from agent_eval_lab.environment import WorldSession
from agent_eval_lab.evaluation import score_run
from agent_eval_lab.prompts import BASELINE_PROMPT, IMPROVED_PROMPT
from agent_eval_lab.provenance import provenance
from agent_eval_lab.schemas import AgentAnswer, Scenario, ToolCall, World

_STORE_KEY = "agent_eval_lab.session"


def _save_session(session: WorldSession) -> None:
    store().set(
        _STORE_KEY,
        {
            "world": session.state.model_dump(mode="json"),
            "trace": [call.model_dump(mode="json") for call in session.trace],
        },
    )


def _tools(session: WorldSession) -> list[Tool]:
    """Build tools bound to a single solve, never to shared mutable task state."""

    def call(name: str, arguments: dict[str, object]) -> str:
        result = session.call(name, arguments)
        _save_session(session)
        return json.dumps(result, ensure_ascii=False)

    @tool
    def lookup_memory() -> Tool:
        async def execute(key: str) -> str:
            """Look up stored user preferences, including their timestamps.

            Args:
                key: Preference key to retrieve.
            """
            return call("lookup_memory", {"key": key})

        return execute

    @tool
    def list_events() -> Tool:
        async def execute(query: str) -> str:
            """Find calendar events matching a query.

            Args:
                query: Search text used to find matching events.
            """
            return call("list_events", {"query": query})

        return execute

    @tool
    def read_email() -> Tool:
        async def execute(email_id: str) -> str:
            """Read a synthetic email by its identifier.

            Args:
                email_id: Identifier of the email to read.
            """
            return call("read_email", {"email_id": email_id})

        return execute

    @tool
    def update_event() -> Tool:
        async def execute(
            event_id: str,
            title: str | None = None,
            date: str | None = None,
            time: str | None = None,
        ) -> str:
            """Update the provided fields of a calendar event.

            Args:
                event_id: Identifier of the event to update.
                title: New title, or omit to leave it unchanged.
                date: New date in YYYY-MM-DD format, or omit to leave it unchanged.
                time: New time in HH:MM format, or omit to leave it unchanged.
            """
            arguments: dict[str, object] = {
                key: value
                for key, value in {
                    "event_id": event_id,
                    "title": title,
                    "date": date,
                    "time": time,
                }.items()
                if value is not None
            }
            return call("update_event", arguments)

        return execute

    return [lookup_memory(), list_events(), read_email(), update_event()]


@solver
def assistant_solver(scenarios: dict[str, Scenario], prompt: str) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        session = WorldSession(scenarios[str(state.sample_id)].world)
        _save_session(session)
        state.messages.insert(0, ChatMessageSystem(content=prompt))
        state.tools = _tools(session)
        return await generate(state, tool_calls="loop")

    return solve


def _all_attempts(state: TaskState, scenario: Scenario, recorded: list[ToolCall]) -> list[ToolCall]:
    """Merge framework-rejected calls into execution order without double counting.

    Inspect validates names/arguments before invoking our tool functions. Those
    failed attempts are visible in messages but never reach WorldSession.call.
    """
    outcomes: dict[str, deque[ChatMessageTool]] = defaultdict(deque)
    for message in state.messages:
        if isinstance(message, ChatMessageTool) and message.tool_call_id is not None:
            outcomes[message.tool_call_id].append(message)
    pending = deque(recorded)
    trace: list[ToolCall] = []
    current = scenario.world.model_copy(deep=True)
    for message in state.messages:
        if not isinstance(message, ChatMessageAssistant):
            continue
        for attempt in message.tool_calls or []:
            result = outcomes[attempt.id].popleft() if outcomes[attempt.id] else None
            if result is None or result.error is not None:
                error = result.error.message if result and result.error else "Tool not executed"
                trace.append(
                    ToolCall(
                        name=attempt.function,
                        arguments=attempt.arguments,
                        result={"ok": False, "error": error, "framework_rejected": True},
                        before=current.model_copy(deep=True),
                        after=current.model_copy(deep=True),
                    )
                )
            else:
                if not pending:
                    raise ValueError("Inspect tool outcome has no matching environment trace")
                call = pending.popleft()
                expected_arguments = dict(attempt.arguments)
                if attempt.function == "update_event":
                    expected_arguments = {
                        key: value
                        for key, value in expected_arguments.items()
                        if key not in {"title", "date", "time"} or value is not None
                    }
                if call.name != attempt.function or call.arguments != expected_arguments:
                    raise ValueError("Inspect tool transcript and environment trace diverged")
                trace.append(call)
                current = call.after.model_copy(deep=True)
    if pending:
        raise ValueError("Environment trace contains unaccounted tool calls")
    return trace


@scorer(metrics=[accuracy()])
def deterministic_checks(scenarios: dict[str, Scenario]) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        scenario = scenarios[str(state.sample_id)]
        session = WorldSession(scenario.world)
        snapshot = store().get(_STORE_KEY)
        if snapshot is not None:
            session.state = World.model_validate(snapshot["world"])
            session.trace = [ToolCall.model_validate(call) for call in snapshot["trace"]]
        session.trace = _all_attempts(state, scenario, session.trace)
        try:
            final = AgentAnswer.model_validate_json(state.output.completion)
        except (ValidationError, ValueError):
            final = None
        result = score_run(scenario, session, final)
        return Score(
            value=int(result.passed),
            answer=state.output.completion,
            explanation="; ".join(result.failures) or "All deterministic checks passed.",
            metadata={
                "checks": result.checks,
                "failures": result.failures,
                "family": scenario.family,
                "tool_calls": len(session.trace),
                "world": session.state.model_dump(mode="json"),
                "trace": [call.model_dump(mode="json") for call in session.trace],
            },
        )

    return score


@task
def assistant_eval(
    variant: str = "improved", split: str = "dev", dataset_path: str | None = None
) -> Task:
    """Evaluate an assistant using a selected Inspect model (no model is hardcoded).

    Example: inspect eval src/agent_eval_lab/inspect_task.py --model PROVIDER/MODEL
    -T variant=improved -T split=dev. Inspect logs include score checks and traces.
    """
    prompts = {"baseline": BASELINE_PROMPT, "improved": IMPROVED_PROMPT}
    if variant not in prompts:
        raise ValueError("variant must be baseline or improved")
    if split not in {"dev", "test"}:
        raise ValueError("split must be dev or test")
    scenarios = load_scenarios(Path(dataset_path) if dataset_path else None, split=split)
    indexed = {scenario.id: scenario for scenario in scenarios}
    return Task(
        dataset=[
            Sample(input=scenario.request, id=scenario.id, metadata={"family": scenario.family})
            for scenario in scenarios
        ],
        solver=assistant_solver(indexed, prompts[variant]),
        scorer=deterministic_checks(indexed),
        config=GenerateConfig(max_tokens=1024, parallel_tool_calls=False),
        message_limit=30,
        token_limit=30_000,
        turn_limit=10,
        time_limit=120,
        metadata={
            "variant": variant,
            "split": split,
            "evaluation_kind": "model",
            "dataset_hash": dataset_hash(scenarios),
            "prompt_hash": hashlib.sha256(prompts[variant].encode()).hexdigest(),
            **provenance(),
        },
        version="1.0.0",
    )
