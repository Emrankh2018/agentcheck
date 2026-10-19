"""Strict JSON file input and deterministic report output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Scenario, Trace, ValidationError


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"JSON object contains duplicate key '{key}'")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValidationError(f"JSON contains nonfinite number '{value}'")


def load_json(path: str | Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8-sig"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValidationError(f"Cannot read JSON from '{path}': {exc}") from exc


def load_scenario(path: str | Path) -> Scenario:
    return Scenario.from_dict(load_json(path))


def load_trace(path: str | Path) -> Trace:
    return Trace.from_dict(load_json(path))


def write_json(path: str | Path, value: Any) -> None:
    try:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise ValidationError(f"Cannot write JSON to '{path}': {exc}") from exc
