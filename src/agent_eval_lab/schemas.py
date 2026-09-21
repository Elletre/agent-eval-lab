"""Strict data contracts shared by tools, adapters, and scorers."""

import json
from datetime import date, datetime, time
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TOOL_NAMES = frozenset({"lookup_memory", "list_events", "read_email", "update_event"})
Status = Literal["answered", "updated", "clarification", "blocked"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Memory(Contract):
    key: str = Field(min_length=1)
    value: str = Field(min_length=1)
    updated_at: str

    @field_validator("updated_at")
    @classmethod
    def timestamp_valid(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Memory timestamps require a timezone")
        return value


class Event(Contract):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    date: str
    time: str
    attendees: list[str] = Field(default_factory=list)

    @field_validator("date")
    @classmethod
    def date_valid(cls, value: str) -> str:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use YYYY-MM-DD dates")
        return value

    @field_validator("time")
    @classmethod
    def time_valid(cls, value: str) -> str:
        time.fromisoformat(value)
        if len(value) != 5 or value[2] != ":":
            raise ValueError("Use HH:MM time")
        return value


class Email(Contract):
    id: str = Field(min_length=1)
    subject: str
    body: str


class World(Contract):
    memories: list[Memory] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    emails: list[Email] = Field(default_factory=list)
    failures: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_world(self) -> Self:
        for entries in (self.events, self.emails):
            ids = [item.id for item in entries]
            if len(ids) != len(set(ids)):
                raise ValueError("World IDs must be unique within each resource")
        if set(self.failures) - TOOL_NAMES:
            raise ValueError("Failure injection must name a supported tool")
        return self


class EventUpdate(Contract):
    event_id: str
    changes: dict[str, str]

    @field_validator("changes")
    @classmethod
    def valid_fields(cls, changes: dict[str, str]) -> dict[str, str]:
        if not changes or set(changes) - {"title", "date", "time"}:
            raise ValueError("Updates must change title, date, or time")
        return changes


class ObservationRequirement(Contract):
    tool: str
    arguments: dict[str, str] = Field(default_factory=dict)
    ok: bool = True

    @model_validator(mode="after")
    def valid_observation(self) -> Self:
        allowed = {
            "lookup_memory": {"key"},
            "list_events": {"query"},
            "read_email": {"email_id"},
            "update_event": {"event_id", "title", "date", "time"},
        }
        if self.tool not in allowed:
            raise ValueError("Unknown observation tool")
        if set(self.arguments) - allowed[self.tool]:
            raise ValueError("Unknown observation argument")
        return self


class Expectation(Contract):
    status: Status
    event_updates: list[EventUpdate] = Field(default_factory=list)
    allowed_write_attempts: list[EventUpdate] = Field(default_factory=list)
    required_observations: list[ObservationRequirement] = Field(default_factory=list)
    required_facts: list[str] = Field(default_factory=list)
    required_fact_groups: list[list[str]] = Field(default_factory=list)
    """Each group needs one member present: the same value may be phrased several ways."""
    forbidden_facts: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    max_tool_calls: int = Field(default=8, ge=0, le=20)
    """A loop guard, not an efficiency target: set it above the work the case needs.
    Economy is reported as a diagnostic so that re-checking a write is not a failure."""

    @field_validator("required_fact_groups")
    @classmethod
    def groups_usable(cls, groups: list[list[str]]) -> list[list[str]]:
        for group in groups:
            if not group or any(not member.strip() for member in group):
                raise ValueError("Fact groups need at least one non-empty alternative")
        return groups

    @field_validator("required_tools")
    @classmethod
    def tools_exist(cls, tools: list[str]) -> list[str]:
        if set(tools) - TOOL_NAMES:
            raise ValueError("Unknown required tool")
        return tools


class Scenario(Contract):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]+$")
    family: str = Field(min_length=1)
    split: Literal["dev", "test"]
    request: str = Field(min_length=1)
    world: World
    expectation: Expectation

    @model_validator(mode="after")
    def consistent_expectations(self) -> Self:
        ids = {event.id: event for event in self.world.events}
        updates = self.expectation.event_updates
        if len({update.event_id for update in updates}) != len(updates):
            raise ValueError("Duplicate expected update")
        if updates and self.expectation.status != "updated":
            raise ValueError("Only updated outcomes may authorize mutations")
        for update in updates + self.expectation.allowed_write_attempts:
            if update.event_id not in ids:
                raise ValueError("Expected update refers to nonexistent event")
            Event.model_validate(ids[update.event_id].model_dump() | update.changes)
        return self


class AgentAnswer(Contract):
    status: Status
    answer: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    """Kept for review, never trusted as proof — and never a reason to reject an answer.

    Models often return whole observed records here instead of identifiers. The
    status and the answer are what the scorer grades, so richer evidence is
    normalised to text rather than failing the trial."""

    @field_validator("evidence", mode="before")
    @classmethod
    def as_text(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [
                item if isinstance(item, str) else json.dumps(item, sort_keys=True)
                for item in value
            ]
        return value


class ToolCall(Contract):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    before: World
    after: World


class RunScore(Contract):
    passed: bool
    checks: dict[str, bool]
    failures: list[str]
