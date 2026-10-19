"""Launch with: streamlit run app.py. The core never depends on Streamlit."""

from __future__ import annotations

import json

import streamlit as st

from agentcheck.engine import evaluate
from agentcheck.samples import PROFILES, load_scenarios, make_trace

st.set_page_config(page_title="AgentCheck | Trace evaluation", page_icon="✓", layout="wide")

scenarios = load_scenarios()
profile_labels = {
    "correct": "Correct execution",
    "incorrect": "Incorrect choices or arguments",
    "unauthorized": "Unexpected / unauthorized calls",
}

with st.sidebar:
    st.title("AgentCheck")
    st.caption("A local trace evaluation workbench")
    st.divider()
    scenario_id = st.selectbox(
        "Scenario",
        options=[item.scenario_id for item in scenarios],
        format_func=lambda value: next(
            item.name for item in scenarios if item.scenario_id == value
        ),
    )
    profile = st.selectbox("Simulated profile", options=PROFILES, format_func=profile_labels.get)
    run = st.button("Run Evaluation", type="primary")
    st.divider()
    st.caption("12 fictional scenarios · 3 simulated profiles")
    st.caption("Deterministic rules. No API keys. No tool execution.")

scenario = next(item for item in scenarios if item.scenario_id == scenario_id)
trace = make_trace(scenario, profile)
selection = (scenario_id, profile)

st.title("Inspect the trace. Understand the result.")
st.write(
    "Compare an agent's recorded tool calls with an explicit scenario. "
    "Every score comes with the checks that produced it."
)
st.info(
    "These are simulated execution traces using fictional data. "
    "AgentCheck checks observable conformance; it does not evaluate live LLM "
    "intelligence or model reasoning."
)

with st.expander("About this project"):
    st.write(
        "AgentCheck is an open-source reliability toolkit for repeatable evaluation of "
        "tool selection, arguments, ordering, missing calls, unexpected calls and response text. "
        "The Python engine, command-line interface and this dashboard share one report format."
    )
    st.markdown(
        "**Scoring weights:** selection 20 · arguments 25 · order 15 · missing calls 15 · "
        "unexpected calls 15 · response text 10. Inapplicable categories are excluded "
        "and active weights are normalized to 100."
    )

st.subheader(scenario.name)
st.write(scenario.user_request)
st.caption(f"{scenario.scenario_id} | {', '.join(scenario.tags)}")

if run:
    result = evaluate(scenario, trace).to_dict()
    result.update(trace_type="simulated", profile=profile)
    st.session_state["evaluation"] = (selection, result)

stored = st.session_state.get("evaluation")
if stored is None or stored[0] != selection:
    st.warning("Select a scenario and profile, then run the evaluation to see its report.")
    with st.expander("Preview simulated trace", expanded=True):
        st.json(trace.to_dict(), expanded=2)
else:
    report = stored[1]
    score_col, passed_col, failed_col, export_col = st.columns([1, 1, 1, 1.5])
    score_col.metric("Overall score", f"{report['score']:g} / 100")
    passed_col.metric("Passed checks", report["passed_checks"])
    failed_col.metric("Failed checks", report["failed_checks"])
    with export_col:
        st.download_button(
            "Download JSON report",
            data=json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            file_name=f"{scenario_id}-{profile}.json",
            mime="application/json",
        )
    if report["failed_checks"]:
        st.warning("Review the failed checks below before accepting this execution.")
    else:
        st.success("Every applicable check passed for this simulated execution.")

    result_tab, calls_tab, scenario_tab = st.tabs(
        ["Checks & breakdown", "Expected vs actual", "Scenario & raw report"]
    )
    with result_tab:
        categories = report["categories"]
        rows = [
            {
                "Category": category["label"],
                "Base weight": category["weight"],
                "Score / 100": category["score"],
                "Status": "Active" if category["active"] else "Not applicable",
            }
            for category in categories
        ]
        st.dataframe(rows, hide_index=True)
        st.caption(
            "Base weights are normalized across active categories; "
            "scores are rounded to 2 decimals."
        )
        for category in categories:
            if not category["active"]:
                continue
            failed = sum(not check["passed"] for check in category["checks"])
            with st.expander(
                f"{category['label']} — {failed} failed / {len(category['checks'])} checks",
                expanded=failed > 0,
            ):
                for check in category["checks"]:
                    if check["passed"]:
                        st.success(check["message"])
                    else:
                        st.error(check["message"])
    with calls_tab:
        expected_col, actual_col = st.columns(2)
        with expected_col:
            st.markdown("#### Expected calls")
            if not report["expected_calls"]:
                st.info("No tool calls expected. Answer or clarify using the supplied information.")
            for index, call in enumerate(report["expected_calls"], 1):
                st.markdown(f"**{index}. {call['name']}**")
                st.json(call["arguments"])
        with actual_col:
            st.markdown("#### Actual calls · simulated")
            if not report["actual_calls"]:
                st.info("This trace contains no tool calls.")
            for index, call in enumerate(report["actual_calls"], 1):
                st.markdown(f"**{index}. {call['name']}**")
                st.json(call["arguments"])
        st.markdown("#### Final response")
        st.write(report["final_response"])
    with scenario_tab:
        st.markdown("#### Scenario definition")
        st.json(scenario.to_dict(), expanded=2)
        st.markdown("#### Evaluation report")
        st.json(report, expanded=False)
