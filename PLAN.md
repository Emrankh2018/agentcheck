# AgentCheck MVP implementation plan

Acceptance: deterministic scenario/trace evaluation; 12 fictional scenarios and three
simulated profiles; usable CLI, Streamlit dashboard and JSON reports; automated tests,
lint, packaging and startup checks; one focused review and fix pass; GitHub delivery.

Architecture: validated immutable models feed a pure evaluator. CLI and dashboard
consume the same report. Bundled JSON fixtures travel inside the Python package.
An adapter protocol describes future normalization without any live integrations.

Dependencies: Python 3.11+, Streamlit; pytest, Ruff and build for development.
Core validation, matching, scoring, JSON and CLI use the standard library.

Failure points: duplicate-name alignment, missing/extra calls, empty expectations,
JSON type equality, nonfinite numbers, malformed files, stale UI selections, package
data omission, and threshold exit status. Test those boundaries directly. Tool calls
are inert data throughout; no execution or dynamic dispatch exists.

Verification: pytest including Streamlit AppTest; Ruff; CLI examples and threshold
failures; build wheel/sdist and run wheel from outside checkout; start Streamlit and
check health. Review once, correct concrete defects, then rerun verification.

Visual direction: white (#FFFFFF), pale slate (#F1F5FA), ink (#192C46), blue
(#2455B2), green (#18734B), red (#B4323A). System sans typography; left-aligned
workbench, sidebar scenario controls, report tabs and native comparison columns.
The trace comparison carries the visual emphasis. No external fonts or animation.
