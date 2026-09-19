"""Allowlisted in-memory tools. Never touches real calendars or external services."""

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from agent_eval_lab.schemas import Event, ToolCall, World


class WorldSession:
    """One isolated world per trial; failed and successful attempts are both recorded."""

    def __init__(self, world: World):
        self.state = world.model_copy(deep=True)
        self.trace: list[ToolCall] = []

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        before = self.state.model_copy(deep=True)
        try:
            result = self._dispatch(name, arguments)
        except (ValueError, TypeError, KeyError, ValidationError) as exc:
            # Tool input errors are observations. Unexpected programming errors propagate.
            result = {"ok": False, "error": str(exc)}
        self.trace.append(
            ToolCall(
                name=name,
                arguments=deepcopy(arguments),
                result=deepcopy(result),
                before=before,
                after=self.state.model_copy(deep=True),
            )
        )
        return deepcopy(result)

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        signatures = {
            "lookup_memory": ({"key"}, {"key"}),
            "list_events": ({"query"}, {"query"}),
            "read_email": ({"email_id"}, {"email_id"}),
            "update_event": ({"event_id", "title", "date", "time"}, {"event_id"}),
        }
        if name not in signatures:
            raise ValueError(f"Unknown tool: {name}")
        allowed, required = signatures[name]
        if set(arguments) - allowed or required - set(arguments):
            raise ValueError(f"Invalid argument names for {name}")
        if any(not isinstance(v, str) for v in arguments.values()):
            raise ValueError("All tool arguments must be strings")
        if name in self.state.failures:
            return {"ok": False, "error": self.state.failures[name]}
        if name == "lookup_memory":
            return {
                "ok": True,
                "memories": [
                    item.model_dump()
                    for item in self.state.memories
                    if item.key == arguments["key"]
                ],
            }
        if name == "list_events":
            query = arguments["query"].casefold()
            return {
                "ok": True,
                "events": [
                    item.model_dump()
                    for item in self.state.events
                    if any(query in value.casefold() for value in (item.title, item.id, item.date))
                ],
            }
        if name == "read_email":
            for email in self.state.emails:
                if email.id == arguments["email_id"]:
                    return {"ok": True, "email": email.model_dump()}
            return {"ok": False, "error": "Email not found"}
        changes = {key: value for key, value in arguments.items() if key != "event_id"}
        if not changes:
            raise ValueError("Provide at least one event change")
        for index, event in enumerate(self.state.events):
            if event.id == arguments["event_id"]:
                updated = Event.model_validate(event.model_dump() | changes)
                self.state.events[index] = updated
                return {"ok": True, "event": updated.model_dump()}
        return {"ok": False, "error": "Event not found"}
