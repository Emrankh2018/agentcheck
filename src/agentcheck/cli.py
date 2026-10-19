"""Command-line evaluation; stdout is JSON, routine errors go to stderr."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence

from .engine import evaluate
from .io import load_scenario, load_trace, write_json
from .models import ValidationError


def _threshold(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("threshold must be a number from 0 to 100") from exc
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise argparse.ArgumentTypeError("threshold must be a finite number from 0 to 100")
    return number


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentcheck", description="Evaluate recorded tool-call data deterministically."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("evaluate", help="Compare scenario and trace JSON files")
    single.add_argument("--scenario", required=True)
    single.add_argument("--trace", required=True)
    samples = commands.add_parser("samples", help="Evaluate all bundled simulated scenarios")
    samples.add_argument(
        "--profile", choices=("correct", "incorrect", "unauthorized"), default="correct"
    )
    for command in (single, samples):
        command.add_argument("--output", help="Also write the JSON report to this file")
        command.add_argument("--threshold", type=_threshold, default=0.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            report = evaluate(load_scenario(args.scenario), load_trace(args.trace))
            reports = [report]
            result = report.to_dict()
        else:
            from .samples import load_scenarios, make_trace

            scenarios = load_scenarios()
            if not scenarios:
                raise ValidationError("No bundled scenarios are available")
            reports = [evaluate(item, make_trace(item, args.profile)) for item in scenarios]
            result = {
                "schema_version": "1.0",
                "trace_type": "simulated",
                "profile": args.profile,
                "reports": [report.to_dict() for report in reports],
                "mean_score": round(sum(report.score for report in reports) / len(reports), 2),
            }
        if args.output:
            write_json(args.output, result)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 1 if any(report.score < args.threshold for report in reports) else 0
    except (ValidationError, RecursionError) as exc:
        print(f"agentcheck: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
