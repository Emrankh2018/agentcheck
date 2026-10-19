"""Fictional, simulated fixtures; never execute the calls they describe."""

from __future__ import annotations

import json
from copy import deepcopy
from importlib.resources import files

from agentcheck.models import Scenario, Trace, ValidationError

PROFILES = ("correct", "incorrect", "unauthorized")


def load_scenarios() -> list[Scenario]:
    """Read packaged fictional scenarios and enforce unique scenario IDs."""
    data = json.loads(files("agentcheck").joinpath("data/scenarios.json").read_text("utf-8"))
    scenarios = [Scenario.from_dict(item) for item in data]
    ids = [scenario.scenario_id for scenario in scenarios]
    if len(set(ids)) != len(ids):
        raise ValidationError("Bundled scenario IDs must be unique.")
    return scenarios


def make_trace(scenario: Scenario, profile: str = "correct") -> Trace:
    """Generate an explicitly simulated execution trace for one scenario."""
    if profile not in PROFILES:
        raise ValidationError(f"Unknown profile {profile!r}; choose one of {PROFILES}.")
    calls = deepcopy(scenario.to_dict()["expected_calls"])
    response = " ".join(scenario.required_response_text) or "Your request is complete."
    if profile == "incorrect":
        if calls:
            calls[0]["arguments"] = {"incorrect_reference": "SIM-WRONG"}
            if len(calls) > 1:
                calls[1]["name"] = "unrelated_search"
        else:
            calls.append({"name": "unrelated_search", "arguments": {"query": "SIM-WRONG"}})
        response = "The simulated request could not be completed."
    elif profile == "unauthorized":
        calls.append({"name": "export_customer_records", "arguments": {"scope": "fictional"}})
    return Trace.from_dict(
        {"scenario_id": scenario.scenario_id, "actual_calls": calls, "final_response": response}
    )
