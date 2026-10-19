# Local verification receipt

Verified 2026-10-19 on Windows, Python 3.11.16. Commands were run through the
machine's RTK proxy; below are the underlying commands for portability.

| Check | Actual result |
| --- | --- |
| `python -m pytest -q` | 89 passed, including Streamlit AppTest and CLI subprocess checks |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | All checked files already formatted |
| `python -m compileall -q src app.py` | Exit 0 |
| `python -m build --no-isolation` | Wheel and source archive built successfully |
| Isolated wheel install with `--no-deps`; run `python -m agentcheck samples --profile correct --threshold 100` outside the checkout root | 12 scenarios, mean 100, exit 0; no Streamlit installed in this environment |
| Source archive inspection | Dashboard, Streamlit config, examples, test fixtures and screenshot included |
| `python -m agentcheck evaluate --scenario examples/scenario.json --trace examples/trace_incorrect.json --threshold 80 --output reports/example-incorrect.json` | Score 75, 1 failed check, exit 1 as expected; JSON exported |
| `python -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false` | Server started; HTTP health endpoint returned `ok` |
| Chrome browser | Real page rendered; Run Evaluation produced 100/100, 10 passed, 0 failed; screenshot saved as `docs/dashboard.jpg` |

One focused review found report-evidence aliasing and incomplete source packaging.
Two added regression tests failed before the copy fix and passed afterward.
The complete suite was rerun after those fixes. No benchmark or live LLM test was
performed; all profiles are simulated and all customer/transaction data fictional.

GitHub Actions provides separate Linux verification on Python 3.11, 3.12 and 3.13.
Local results above do not establish remote CI status; inspect the repository's
Actions run for that evidence.
