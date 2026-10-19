import math

import pytest

from agentcheck import Scenario, ToolCall, Trace, ValidationError
from agentcheck.io import load_json, load_scenario, load_trace


def test_round_trip(scenario, trace):
    assert Scenario.from_dict(scenario.to_dict()) == scenario
    assert Trace.from_dict(trace.to_dict()) == trace


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("scenario_id", " ", "non-empty string"),
        ("name", 1, "non-empty string"),
        ("user_request", None, "non-empty string"),
        ("allowed_tools", "lookup_order", "list of strings"),
        ("allowed_tools", ["lookup_order", "lookup_order"], "duplicates"),
        ("allowed_tools", [], "not in allowed_tools"),
        ("tags", ["support", "support"], "duplicates"),
        ("required_response_text", [""], "non-empty string"),
        ("expected_calls", {}, "list of tool-call objects"),
    ],
)
def test_invalid_scenario(scenario, field, value, message):
    data = scenario.to_dict()
    data[field] = value
    with pytest.raises(ValidationError, match=message):
        Scenario.from_dict(data)


@pytest.mark.parametrize("factory", [Scenario.from_dict, Trace.from_dict, ToolCall.from_dict])
def test_input_must_be_object(factory):
    with pytest.raises(ValidationError, match="JSON object"):
        factory([])


@pytest.mark.parametrize("kind", ["scenario", "trace"])
def test_unknown_and_missing_fields(scenario, trace, kind):
    model = scenario if kind == "scenario" else trace
    factory = type(model).from_dict
    data = model.to_dict()
    data["typo"] = True
    with pytest.raises(ValidationError, match="unknown fields: typo"):
        factory(data)
    data = model.to_dict()
    del data["scenario_id"]
    with pytest.raises(ValidationError, match="missing required fields: scenario_id"):
        factory(data)


@pytest.mark.parametrize("arguments", [[], {"x": math.nan}, {"x": math.inf}, {1: "x"}, {"x": (1,)}])
def test_invalid_arguments(arguments):
    with pytest.raises(ValidationError):
        ToolCall("lookup", arguments)


def test_circular_argument_rejected():
    arguments = {}
    arguments["self"] = arguments
    with pytest.raises(ValidationError, match="circular reference"):
        ToolCall("lookup", arguments)


def test_constructor_validates_calls():
    with pytest.raises(ValidationError, match="must be a ToolCall"):
        Trace("demo", [{"name": "x", "arguments": {}}], "")


def test_optional_fields_default(scenario):
    data = scenario.to_dict()
    del data["required_response_text"]
    del data["tags"]
    result = Scenario.from_dict(data)
    assert result.tags == result.required_response_text == []


@pytest.mark.parametrize("field,value", [("scenario_id", ""), ("final_response", 1)])
def test_invalid_trace(trace, field, value):
    data = trace.to_dict()
    data[field] = value
    with pytest.raises(ValidationError, match=field):
        Trace.from_dict(data)


def test_nested_call_error_has_index(trace):
    data = trace.to_dict()
    data["actual_calls"] = [{"name": "x", "arguments": []}]
    with pytest.raises(ValidationError, match=r"actual_calls\[0\].*arguments"):
        Trace.from_dict(data)


@pytest.mark.parametrize(
    "content,message",
    [('{"x":1,"x":2}', "duplicate key"), ('{"x":NaN}', "nonfinite"), ("{", "Cannot read JSON")],
)
def test_invalid_json_file(tmp_path, content, message):
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValidationError, match=message):
        load_json(path)


def test_file_loaders(tmp_path, scenario, trace):
    import json

    scenario_path, trace_path = tmp_path / "scenario.json", tmp_path / "trace.json"
    scenario_path.write_text(json.dumps(scenario.to_dict()), encoding="utf-8")
    trace_path.write_text(json.dumps(trace.to_dict()), encoding="utf-8")
    assert load_scenario(scenario_path) == scenario
    assert load_trace(trace_path) == trace
    with pytest.raises(ValidationError, match="Cannot read JSON"):
        load_json(tmp_path / "missing.json")
