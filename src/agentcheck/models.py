"""Validated, JSON-only input models. Tool calls are inert data."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


class ValidationError(ValueError):
    """An input does not satisfy the AgentCheck schema."""


def _string(value: Any, path: str, *, nonempty: bool = True) -> None:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        qualifier = "non-empty " if nonempty else ""
        raise ValidationError(f"{path} must be a {qualifier}string")


def _object(value: Any, path: str, required: set[str], optional: set[str]) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be a JSON object")
    missing = required - value.keys()
    if missing:
        raise ValidationError(f"{path} missing required fields: {', '.join(sorted(missing))}")
    unknown = value.keys() - required - optional
    if unknown:
        raise ValidationError(
            f"{path} contains unknown fields: {', '.join(sorted(map(str, unknown)))}"
        )


def _strings(value: Any, path: str, *, unique: bool = False) -> None:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be a list of strings")
    for index, item in enumerate(value):
        _string(item, f"{path}[{index}]")
    if unique and len(set(value)) != len(value):
        raise ValidationError(f"{path} must not contain duplicates")


def _json(value: Any, path: str, ancestors: set[int] | None = None) -> None:
    """Reject non-JSON Python types, nonfinite numbers and recursive containers."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(f"{path} must contain only finite numbers")
        return
    if not isinstance(value, (dict, list)):
        raise ValidationError(f"{path} contains a non-JSON value ({type(value).__name__})")
    ancestors = set() if ancestors is None else ancestors
    if id(value) in ancestors:
        raise ValidationError(f"{path} contains a circular reference")
    ancestors.add(id(value))
    try:
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValidationError(f"{path} object keys must be strings")
                _json(item, f"{path}.{key}", ancestors)
        else:
            for index, item in enumerate(value):
                _json(item, f"{path}[{index}]", ancestors)
    finally:
        ancestors.remove(id(value))


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        _string(self.name, "tool call.name")
        if not isinstance(self.arguments, dict):
            raise ValidationError("tool call.arguments must be a JSON object")
        _json(self.arguments, "tool call.arguments")

    @classmethod
    def from_dict(cls, value: Any) -> ToolCall:
        _object(value, "tool call", {"name", "arguments"}, set())
        return cls(value["name"], value["arguments"])

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": deepcopy(self.arguments)}


def _calls(value: Any, path: str) -> None:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be a list of ToolCall objects")
    for index, item in enumerate(value):
        if not isinstance(item, ToolCall):
            raise ValidationError(f"{path}[{index}] must be a ToolCall")
        item.__post_init__()


def _parse_calls(value: Any, path: str) -> list[ToolCall]:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be a list of tool-call objects")
    calls = []
    for index, item in enumerate(value):
        try:
            calls.append(ToolCall.from_dict(item))
        except ValidationError as exc:
            raise ValidationError(f"{path}[{index}]: {exc}") from exc
    return calls


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    user_request: str
    allowed_tools: list[str]
    expected_calls: list[ToolCall]
    required_response_text: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for key in ("scenario_id", "name", "user_request"):
            _string(getattr(self, key), f"scenario.{key}")
        _strings(self.allowed_tools, "scenario.allowed_tools", unique=True)
        _strings(self.required_response_text, "scenario.required_response_text")
        _strings(self.tags, "scenario.tags", unique=True)
        _calls(self.expected_calls, "scenario.expected_calls")
        for index, call in enumerate(self.expected_calls):
            if call.name not in self.allowed_tools:
                raise ValidationError(
                    f"scenario.expected_calls[{index}] tool '{call.name}' is not in allowed_tools"
                )

    @classmethod
    def from_dict(cls, value: Any) -> Scenario:
        required = {"scenario_id", "name", "user_request", "allowed_tools", "expected_calls"}
        _object(value, "scenario", required, {"required_response_text", "tags"})
        return cls(
            scenario_id=value["scenario_id"],
            name=value["name"],
            user_request=value["user_request"],
            allowed_tools=value["allowed_tools"],
            expected_calls=_parse_calls(value["expected_calls"], "scenario.expected_calls"),
            required_response_text=value.get("required_response_text", []),
            tags=value.get("tags", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "user_request": self.user_request,
            "allowed_tools": list(self.allowed_tools),
            "expected_calls": [call.to_dict() for call in self.expected_calls],
            "required_response_text": list(self.required_response_text),
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class Trace:
    scenario_id: str
    actual_calls: list[ToolCall]
    final_response: str

    def __post_init__(self) -> None:
        _string(self.scenario_id, "trace.scenario_id")
        _calls(self.actual_calls, "trace.actual_calls")
        _string(self.final_response, "trace.final_response", nonempty=False)

    @classmethod
    def from_dict(cls, value: Any) -> Trace:
        _object(value, "trace", {"scenario_id", "actual_calls", "final_response"}, set())
        return cls(
            value["scenario_id"],
            _parse_calls(value["actual_calls"], "trace.actual_calls"),
            value["final_response"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "actual_calls": [call.to_dict() for call in self.actual_calls],
            "final_response": self.final_response,
        }
