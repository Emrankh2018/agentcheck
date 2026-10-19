import json
from dataclasses import replace

import pytest

from agentcheck import Scenario, ToolCall, Trace, ValidationError, evaluate


def category(report, key):
    return next(item for item in report.categories if item.key == key)


def test_correct_execution(scenario, trace):
    report = evaluate(scenario, trace)
    assert report.score == 100
    assert report.failed_checks == 0
    assert report.passed_checks == 10
    assert all(item.score == 100 for item in report.categories)


def test_wrong_tool_selection(scenario, trace):
    wrong = replace(trace, actual_calls=[ToolCall("search_help", {"query": "order"})])
    report = evaluate(scenario, wrong)
    assert category(report, "tool_selection").score == 0
    assert category(report, "missing_calls").score == 0
    assert "allowed but unexpected" in category(report, "unexpected_calls").checks[0].message
    assert report.score == 10


def test_wrong_argument_exact_weight(scenario, trace):
    wrong = replace(
        trace, actual_calls=[ToolCall("lookup_order", {"order_id": "WRONG"}), trace.actual_calls[1]]
    )
    report = evaluate(scenario, wrong)
    assert report.score == 87.5
    assert category(report, "arguments").score == 50
    assert report.failed_checks == 1
    assert "WRONG" in category(report, "arguments").checks[0].message


def test_missing_call(scenario, trace):
    report = evaluate(scenario, replace(trace, actual_calls=trace.actual_calls[:1]))
    assert category(report, "missing_calls").score == 50
    assert category(report, "arguments").score == 50
    assert category(report, "order").score == 100
    assert report.score == 80


@pytest.mark.parametrize(
    "name,description", [("delete_everything", "unauthorized"), ("search_help", "unexpected")]
)
def test_extra_call(scenario, trace, name, description):
    report = evaluate(
        scenario, replace(trace, actual_calls=trace.actual_calls + [ToolCall(name, {})])
    )
    assert report.score == 88.33
    assert category(report, "arguments").score == 100
    assert description in category(report, "unexpected_calls").checks[-1].message


def test_duplicate_extra_occurrence(scenario, trace):
    report = evaluate(
        scenario, replace(trace, actual_calls=trace.actual_calls + trace.actual_calls[:1])
    )
    assert category(report, "unexpected_calls").checks[-1].passed is False


def test_wrong_order(scenario, trace):
    report = evaluate(scenario, replace(trace, actual_calls=list(reversed(trace.actual_calls))))
    assert report.score == 85
    assert category(report, "arguments").score == 100
    assert category(report, "order").score == 0


def test_empty_actual_sequence(scenario, trace):
    report = evaluate(scenario, replace(trace, actual_calls=[]))
    assert report.score == 25
    assert category(report, "order").score == 0
    assert category(report, "unexpected_calls").score == 100


def test_empty_expected_and_actual_fairly_score_full_marks():
    scenario = Scenario("no-tools", "Greeting", "Say hello", [], [])
    report = evaluate(scenario, Trace("no-tools", [], "Hello"))
    assert report.score == 100
    assert [cat.key for cat in report.categories if cat.active] == [
        "tool_selection",
        "unexpected_calls",
    ]
    assert all(cat.score is None for cat in report.categories if not cat.active)


def test_empty_expected_with_extra_calls():
    scenario = Scenario("no-tools", "Greeting", "Say hello", ["lookup"], [])
    report = evaluate(scenario, Trace("no-tools", [ToolCall("lookup", {})], "Hello"))
    assert report.score == 0
    assert report.failed_checks == 2


def test_response_case_insensitive_and_each_fragment_checked(scenario, trace):
    scenario = replace(scenario, required_response_text=["ORDER UPDATE", "confirmed"])
    report = evaluate(scenario, trace)
    assert report.score == 95
    assert category(report, "response_text").score == 50
    assert "confirmed" in category(report, "response_text").checks[1].message


def test_all_checks_can_fail(scenario):
    report = evaluate(scenario, Trace(scenario.scenario_id, [ToolCall("unauthorized", {})], ""))
    assert report.score == 0
    assert report.passed_checks == 0


def test_inactive_response_weight_is_normalized(scenario, trace):
    scenario = replace(scenario, required_response_text=[])
    trace = replace(trace, actual_calls=list(reversed(trace.actual_calls)))
    report = evaluate(scenario, trace)
    assert report.score == 83.33
    assert category(report, "response_text").active is False


@pytest.mark.parametrize(
    "expected,actual,score",
    [
        ({"x": True}, {"x": 1}, 0),
        ({"x": 0}, {"x": False}, 0),
        ({"x": [1, 2]}, {"x": [2, 1]}, 0),
        ({"a": 1, "b": {"c": None}}, {"b": {"c": None}, "a": 1}, 100),
        ({"x": 1}, {"x": 1.0}, 100),
        ({"x": "1"}, {"x": 1}, 0),
        ({"x": [True]}, {"x": [1]}, 0),
        ({"x": 1}, {"x": 1, "extra": 2}, 0),
    ],
)
def test_structural_argument_comparison(expected, actual, score):
    scenario = Scenario("args", "Arguments", "Test", ["lookup"], [ToolCall("lookup", expected)])
    report = evaluate(scenario, Trace("args", [ToolCall("lookup", actual)], ""))
    assert category(report, "arguments").score == score


def test_repeated_tools_pair_by_occurrence():
    expected = [ToolCall("lookup", {"id": 1}), ToolCall("lookup", {"id": 2})]
    scenario = Scenario("repeat", "Repeat", "Test", ["lookup"], expected)
    report = evaluate(scenario, Trace("repeat", list(reversed(expected)), ""))
    assert category(report, "arguments").score == 0
    assert category(report, "order").score == 100


def test_mismatched_id_rejected(scenario, trace):
    with pytest.raises(ValidationError, match="does not match"):
        evaluate(scenario, replace(trace, scenario_id="other"))


def test_raw_dict_is_not_accepted(scenario, trace):
    with pytest.raises(ValidationError, match="requires a Scenario and a Trace"):
        evaluate(scenario.to_dict(), trace)


def test_mutated_models_are_revalidated(scenario, trace):
    trace.actual_calls[0].arguments["invalid"] = float("nan")
    with pytest.raises(ValidationError, match="finite"):
        evaluate(scenario, trace)


def test_report_json_stable_complete(scenario, trace):
    report = evaluate(scenario, trace)
    data = json.loads(report.to_json())
    assert data == report.to_dict()
    assert data["schema_version"] == "1.0"
    assert data["expected_calls"] == scenario.to_dict()["expected_calls"]
    assert data["actual_calls"] == trace.to_dict()["actual_calls"]
    assert data["final_response"] == trace.final_response
    assert data["categories"][0]["checks"][0]["expected_index"] == 0
    assert report.to_json() == evaluate(scenario, trace).to_json()


def test_report_preserves_evidence_when_inputs_change(scenario, trace):
    report = evaluate(scenario, trace)
    snapshot = report.to_json()
    trace.actual_calls[0].arguments["order_id"] = "SIM-CHANGED"
    scenario.expected_calls.clear()
    trace.actual_calls.clear()
    assert report.to_json() == snapshot


def test_exported_report_is_detached(scenario, trace):
    report = evaluate(scenario, trace)
    snapshot = report.to_json()
    exported = report.to_dict()
    exported["expected_calls"][0]["arguments"]["order_id"] = "SIM-CHANGED"
    exported["actual_calls"][0]["arguments"]["nested"] = ["changed"]
    assert report.to_json() == snapshot
