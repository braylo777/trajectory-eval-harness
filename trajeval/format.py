"""JSONL trajectory format.

One JSON object per line. See docs/TRAJECTORY_FORMAT.md.
"""

from __future__ import annotations

import json
from pathlib import Path

class FormatError(ValueError):
    pass


REQUIRED = ("id", "task_id", "source", "task", "steps", "final_answer")
OPTIONAL = ("seed", "params", "meta")
SOURCES = ("synthetic", "human", "production")
STEP_REQUIRED = ("tool", "arguments", "observation")
STEP_OPTIONAL = ("argument_schema", "observation_schema", "thought")


def canonical(value) -> str:
    """Stable JSON for comparisons. Key order does not matter."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def dumps_trajectory(trajectory: dict) -> str:
    return json.dumps(trajectory, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def dump_jsonl_text(trajectories: list[dict]) -> str:
    if not trajectories:
        return ""
    return "\n".join(dumps_trajectory(t) for t in trajectories) + "\n"


def dump_jsonl(path: str | Path, trajectories: list[dict]) -> None:
    Path(path).write_text(dump_jsonl_text(trajectories), encoding="utf-8")


def dump_json(path: str | Path, obj) -> None:
    Path(path).write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | Path) -> list[dict]:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    rows: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FormatError(f"{file}:{lineno}: invalid JSON ({exc.msg})") from exc
        validate_trajectory(obj, lineno=lineno)
        rows.append(obj)
    ids = [row["id"] for row in rows]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise FormatError(f"{file}: duplicate trajectory id(s): {', '.join(duplicates)}")
    return rows


def validate_trajectory(obj, lineno: int | None = None) -> None:
    prefix = f"line {lineno}: " if lineno else ""
    if not isinstance(obj, dict):
        raise FormatError(prefix + "trajectory must be a JSON object")
    unknown = sorted(set(obj) - set(REQUIRED) - set(OPTIONAL))
    if unknown:
        raise FormatError(prefix + f"unknown fields: {', '.join(unknown)}")
    for key in REQUIRED:
        if key not in obj:
            raise FormatError(prefix + f"missing {key}")
    _require_str(obj, "id", prefix)
    _require_str(obj, "task_id", prefix)
    _require_str(obj, "task", prefix)
    _require_str(obj, "final_answer", prefix, allow_empty=True)
    if obj["source"] not in SOURCES:
        raise FormatError(prefix + "source must be one of: synthetic, human, production")
    if not isinstance(obj["steps"], list):
        raise FormatError(prefix + "steps must be a list")
    for index, step in enumerate(obj["steps"]):
        _validate_step(step, prefix, index)
    if "params" in obj and not isinstance(obj["params"], dict):
        raise FormatError(prefix + "params must be an object")
    if "seed" in obj and (isinstance(obj["seed"], bool) or not isinstance(obj["seed"], int)):
        raise FormatError(prefix + "seed must be an integer")
    if "meta" in obj and not isinstance(obj["meta"], dict):
        raise FormatError(prefix + "meta must be an object")


def _require_str(obj: dict, key: str, prefix: str, allow_empty: bool = False) -> None:
    value = obj[key]
    if not isinstance(value, str) or (not allow_empty and value == ""):
        raise FormatError(prefix + f"{key} must be a non-empty string")


def _validate_step(step, prefix: str, index: int) -> None:
    where = f"{prefix}step {index}: "
    if not isinstance(step, dict):
        raise FormatError(where + "step must be an object")
    unknown = sorted(set(step) - set(STEP_REQUIRED) - set(STEP_OPTIONAL))
    if unknown:
        raise FormatError(where + f"unknown fields: {', '.join(unknown)}")
    for key in STEP_REQUIRED:
        if key not in step:
            raise FormatError(where + f"missing {key}")
    if not isinstance(step["tool"], str) or step["tool"] == "":
        raise FormatError(where + "tool must be a non-empty string")
    if not isinstance(step["arguments"], dict):
        raise FormatError(where + "arguments must be an object")
    if not _is_json_value(step["observation"]):
        raise FormatError(where + "observation is not valid JSON")
    for schema_key in ("argument_schema", "observation_schema"):
        if schema_key in step and not isinstance(step[schema_key], dict):
            raise FormatError(where + f"{schema_key} must be an object")
    if "thought" in step and not isinstance(step["thought"], str):
        raise FormatError(where + "thought must be a string")


def _is_json_value(value) -> bool:
    if value is None or isinstance(value, (str, bool, int, float)):
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_json_value(v) for k, v in value.items())
    return False
