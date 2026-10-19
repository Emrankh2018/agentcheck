"""Transparent deterministic checks; this module never executes a tool."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .models import Scenario, ToolCall, Trace, ValidationError


@dataclass(frozen=True)
class Check:
    passed: bool
    message: str
    expected_index: int | None = None
    actual_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"passed": self.passed, "message": self.message}
        if self.expected_index is not None:
            result["expected_index"] = self.expected_index
        if self.actual_index is not None:
            result["actual_index"] = self.actual_index
        return result


@dataclass(frozen=True)
class CategoryResult:
    key: str
    label: str
    weight: int
    active: bool
    checks: list[Check]

    @property
    def score(self) -> float | None:
        if not self.active:
            return None
        return round(self.fraction * 100, 2)

    @property
    def fraction(self) -> float:
        return sum(check.passed for check in self.checks) / len(self.checks) if self.checks else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": self.weight,
            "active": self.active,
            "score": self.score,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True)
class EvaluationReport:
    scenario_id: str
    score: float
    categories: list[CategoryResult]
    expected_calls: list[ToolCall]
    actual_calls: list[ToolCall]
    final_response: str

    @property
    def passed_checks(self) -> int:
        return sum(check.passed for cat in self.categories for check in cat.checks)

    @property
    def failed_checks(self) -> int:
        return sum(not check.passed for cat in self.categories for check in cat.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "scenario_id": self.scenario_id,
            "score": self.score,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "categories": [category.to_dict() for category in self.categories],
            "expected_calls": [call.to_dict() for call in self.expected_calls],
            "actual_calls": [call.to_dict() for call in self.actual_calls],
            "final_response": self.final_response,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, allow_nan=False)


def _equal(expected: Any, actual: Any) -> bool:
    """JSON structural equality: booleans differ from numbers; arrays are ordered."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, dict) and isinstance(actual, dict):
        return expected.keys() == actual.keys() and all(
            _equal(value, actual[key]) for key, value in expected.items()
        )
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(
            _equal(left, right) for left, right in zip(expected, actual, strict=True)
        )
    return expected == actual


def evaluate(scenario: Scenario, trace: Trace) -> EvaluationReport:
    """Compare same-name call occurrences, then aggregate active weighted checks.

    Each actual call pairs with the first unmatched expected call of that name.
    Arguments cannot influence matching; repeated names pair by occurrence.
    Indices in reports are zero-based. Missing calls fail argument checks too.
    """
    if not isinstance(scenario, Scenario) or not isinstance(trace, Trace):
        raise ValidationError("evaluate requires a Scenario and a Trace")
    scenario.__post_init__()
    trace.__post_init__()
    if scenario.scenario_id != trace.scenario_id:
        raise ValidationError(
            f"trace.scenario_id '{trace.scenario_id}' does not match "
            f"scenario.scenario_id '{scenario.scenario_id}'"
        )
    expected, actual = scenario.expected_calls, trace.actual_calls
    by_expected: dict[int, int] = {}
    by_actual: dict[int, int] = {}
    for actual_index, call in enumerate(actual):
        for expected_index, desired in enumerate(expected):
            if expected_index not in by_expected and call.name == desired.name:
                by_expected[expected_index] = actual_index
                by_actual[actual_index] = expected_index
                break

    selection = []
    unexpected = []
    for index, call in enumerate(actual):
        matched = index in by_actual
        allowed = call.name in scenario.allowed_tools
        selection.append(
            Check(
                matched,
                f"Actual call {index} '{call.name}' matches an expected occurrence."
                if matched
                else f"Actual call {index} '{call.name}' has no expected occurrence; "
                "remove it or correct the tool name.",
                by_actual.get(index),
                index,
            )
        )
        unexpected.append(
            Check(
                matched and allowed,
                f"Actual call {index} '{call.name}' is expected and authorized."
                if matched and allowed
                else (
                    f"Actual call {index} '{call.name}' is unauthorized; use only allowed_tools."
                    if not allowed
                    else f"Actual call {index} '{call.name}' is allowed but unexpected; "
                    "remove the extra call."
                ),
                by_actual.get(index),
                index,
            )
        )
    if not actual:
        selection.append(
            Check(
                not expected,
                "No tools were expected or selected."
                if not expected
                else "No tools were selected; execute the expected call sequence.",
            )
        )
        unexpected.append(Check(True, "No unexpected or unauthorized calls occurred."))

    arguments, missing = [], []
    for index, call in enumerate(expected):
        actual_index = by_expected.get(index)
        present = actual_index is not None
        received_arguments = actual[actual_index].arguments if present else None
        correct = present and _equal(call.arguments, received_arguments)
        arguments.append(
            Check(
                correct,
                f"Expected call {index} '{call.name}' has correct arguments."
                if correct
                else (
                    f"Call {index} '{call.name}' is missing; provide the expected arguments."
                    if not present
                    else f"Arguments differ for expected call {index} '{call.name}'; "
                    f"expected {json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)}, "
                    "received "
                    f"{json.dumps(received_arguments, sort_keys=True, ensure_ascii=False)}."
                ),
                index,
                actual_index,
            )
        )
        missing.append(
            Check(
                present,
                f"Expected call {index} '{call.name}' is present."
                if present
                else f"Expected call {index} '{call.name}' is missing; "
                "add this call in the specified order.",
                index,
                actual_index,
            )
        )

    indices = list(by_actual.values())
    ordered = bool(indices) and indices == sorted(indices)
    order = (
        [
            Check(
                ordered,
                "Matched calls preserve expected relative order."
                if ordered
                else "No expected calls matched; provide the expected sequence."
                if not indices
                else "Matched calls are out of order; follow the expected_calls sequence.",
            )
        ]
        if expected
        else []
    )
    response = [
        Check(
            text.casefold() in trace.final_response.casefold(),
            f"Final response contains required text {text!r}."
            if text.casefold() in trace.final_response.casefold()
            else f"Final response is missing required text {text!r}; include it in the response.",
        )
        for text in scenario.required_response_text
    ]
    categories = [
        CategoryResult("tool_selection", "Tool selection", 20, True, selection),
        CategoryResult("arguments", "Argument correctness", 25, bool(expected), arguments),
        CategoryResult("order", "Call ordering", 15, bool(expected), order),
        CategoryResult("missing_calls", "Missing calls", 15, bool(expected), missing),
        CategoryResult("unexpected_calls", "Unexpected / unauthorized calls", 15, True, unexpected),
        CategoryResult("response_text", "Required response text", 10, bool(response), response),
    ]
    active = [category for category in categories if category.active]
    score = round(
        100
        * sum(category.weight * category.fraction for category in active)
        / sum(category.weight for category in active),
        2,
    )
    return EvaluationReport(
        scenario.scenario_id,
        score,
        categories,
        deepcopy(expected),
        deepcopy(actual),
        trace.final_response,
    )
