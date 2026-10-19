import json
import subprocess
import sys

import pytest

from agentcheck.cli import main


@pytest.fixture
def inputs(tmp_path, scenario, trace):
    paths = tmp_path / "scenario.json", tmp_path / "trace.json"
    paths[0].write_text(json.dumps(scenario.to_dict()), encoding="utf-8")
    paths[1].write_text(json.dumps(trace.to_dict()), encoding="utf-8")
    return ["evaluate", "--scenario", str(paths[0]), "--trace", str(paths[1])]


def test_cli_evaluate_and_export(inputs, tmp_path, capsys):
    output = tmp_path / "reports" / "report.json"
    assert main(inputs + ["--threshold", "100", "--output", str(output)]) == 0
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["score"] == 100
    assert json.loads(output.read_text(encoding="utf-8")) == stdout


def test_cli_threshold_failure(inputs, capsys):
    trace_path = inputs[-1]
    data = json.loads(open(trace_path, encoding="utf-8").read())
    data["final_response"] = ""
    with open(trace_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    assert main(inputs + ["--threshold", "91"]) == 1
    assert json.loads(capsys.readouterr().out)["score"] == 90
    assert main(inputs + ["--threshold", "90"]) == 0


@pytest.mark.parametrize("threshold", ["-1", "101", "nan", "inf", "abc"])
def test_invalid_threshold(inputs, threshold, capsys):
    with pytest.raises(SystemExit) as exc:
        main(inputs + ["--threshold", threshold])
    assert exc.value.code == 2
    assert "threshold" in capsys.readouterr().err


def test_missing_input_file(capsys):
    assert main(["evaluate", "--scenario", "missing.json", "--trace", "missing.json"]) == 2
    error = capsys.readouterr().err
    assert "Cannot read JSON" in error
    assert "Traceback" not in error


def test_invalid_schema(inputs, capsys):
    with open(inputs[-1], "w", encoding="utf-8") as handle:
        json.dump({"scenario_id": "demo"}, handle)
    assert main(inputs) == 2
    assert "missing required fields" in capsys.readouterr().err


def test_unwritable_report_path(inputs, tmp_path, capsys):
    assert main(inputs + ["--output", str(tmp_path)]) == 2
    assert "Cannot write JSON" in capsys.readouterr().err


def test_cli_samples_correct(capsys):
    assert main(["samples", "--profile", "correct", "--threshold", "100"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["reports"]) == 12
    assert result["mean_score"] == 100
    assert result["trace_type"] == "simulated"
    assert result["profile"] == "correct"


@pytest.mark.parametrize("profile", ["incorrect", "unauthorized"])
def test_cli_samples_imperfect(profile, capsys):
    assert main(["samples", "--profile", profile, "--threshold", "100"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["mean_score"] < 100
    assert all(report["failed_checks"] for report in result["reports"])


def test_module_entry_point():
    completed = subprocess.run(
        [sys.executable, "-m", "agentcheck", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "evaluate" in completed.stdout
