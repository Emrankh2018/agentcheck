import pytest

from agentcheck import Scenario, ToolCall, Trace


@pytest.fixture
def scenario():
    return Scenario(
        scenario_id="support-01",
        name="Fictional order status",
        user_request="Find my fictional order and send an update.",
        allowed_tools=["lookup_order", "send_update", "search_help"],
        expected_calls=[
            ToolCall("lookup_order", {"order_id": "DEMO-101"}),
            ToolCall("send_update", {"channel": "email", "confirmed": True}),
        ],
        required_response_text=["order update"],
        tags=["support"],
    )


@pytest.fixture
def trace(scenario):
    return Trace(scenario.scenario_id, list(scenario.expected_calls), "Your ORDER UPDATE is ready.")
