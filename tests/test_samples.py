import pytest

from agentcheck.engine import evaluate
from agentcheck.models import ValidationError
from agentcheck.samples import PROFILES, load_scenarios, make_trace


def test_fictional_catalog_has_twelve_unique_ids():
    scenarios = load_scenarios()
    assert len(scenarios) == 12
    assert len({scenario.scenario_id for scenario in scenarios}) == 12
    assert any(not scenario.expected_calls for scenario in scenarios)


@pytest.mark.parametrize("scenario", load_scenarios(), ids=lambda scenario: scenario.scenario_id)
def test_profiles_are_distinct_and_reproducible(scenario):
    reports = {profile: evaluate(scenario, make_trace(scenario, profile)) for profile in PROFILES}
    assert reports["correct"].score == 100
    assert reports["incorrect"].score < reports["correct"].score
    assert reports["unauthorized"].score < reports["correct"].score
    assert reports["unauthorized"].failed_checks > 0
    assert make_trace(scenario, "correct").to_dict() == make_trace(scenario, "correct").to_dict()
    assert (
        scenario.to_dict()["expected_calls"]
        == make_trace(scenario, "correct").to_dict()["actual_calls"]
    )


def test_unknown_profile_is_descriptive():
    with pytest.raises(ValidationError, match="Unknown profile"):
        make_trace(load_scenarios()[0], "live")
