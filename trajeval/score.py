"""Per-step scores and the weighted trajectory score.

Alignment is by index. An extra step inserted at position 0 does not shift
the rest into place; later steps are compared at the wrong index and fail.
That is deliberate and tested. It is also a limit.

Default weights:

    tool_choice   0.25
    exact         0.30   (mean of tool name, arguments, observation)
    schema        0.15
    final_answer  0.20
    judge         0.10

`exact` includes the tool name, so a wrong tool fails both `tool_choice` and
`exact`. The weights are not independent evidence. Schema is shape only: a
wrong city string still passes a string schema.

If a golden step has no schema, that component is left out and the remaining
weights are renormalized. Scores are rounded to 6 decimal places.
"""

from __future__ import annotations

from trajeval.format import canonical
from trajeval.judge import MockJudge
from trajeval.schema import validate
from trajeval.text import final_answer_score

WEIGHTS = {
    "tool_choice": 0.25,
    "exact": 0.30,
    "schema": 0.15,
    "final_answer": 0.20,
    "judge": 0.10,
}


def q(value: float) -> float:
    return round(float(value), 6)


def score_trajectory(golden: dict, candidate: dict, judge=None) -> dict:
    judge = judge or MockJudge()
    golden_steps = golden["steps"]
    candidate_steps = candidate["steps"]
    count = max(len(golden_steps), len(candidate_steps))
    rows = []
    schema_values = []
    for index in range(count):
        left = golden_steps[index] if index < len(golden_steps) else None
        right = candidate_steps[index] if index < len(candidate_steps) else None
        row = _score_step(index, golden, left, right, judge, candidate)
        rows.append(row)
        if row["schema"] is not None:
            schema_values.append(row["schema"])

    if count == 0:
        exact = 1.0
        tool_choice = 1.0
        judge_steps = 1.0
    else:
        exact = sum(row["exact"] for row in rows) / count
        tool_choice = sum(row["tool_choice"] for row in rows) / count
        judge_steps = sum(row["judge"] for row in rows) / count

    answer = final_answer_score(golden["final_answer"], candidate["final_answer"])
    answer_judgment = judge.judge_answer(golden["task"], golden["final_answer"], candidate["final_answer"])
    judge_score = 0.7 * judge_steps + 0.3 * answer_judgment.score

    components = {
        "tool_choice": q(tool_choice),
        "exact": q(exact),
        "schema": None if not schema_values else q(sum(schema_values) / len(schema_values)),
        "final_answer": q(answer),
        "judge": q(judge_score),
    }
    notes = [note for row in rows for note in row["notes"]]
    if components["final_answer"] < 1.0:
        notes.append(answer_judgment.rationale)
    return {
        "id": golden["id"],
        "task_id": golden["task_id"],
        "score": _aggregate(components),
        "scorers": {key: value for key, value in components.items() if value is not None},
        "steps": [_public_step(row) for row in rows],
        "notes": notes,
    }


def missing_trajectory(golden: dict) -> dict:
    scorers = {name: 0.0 for name in WEIGHTS}
    return {
        "id": golden["id"],
        "task_id": golden["task_id"],
        "score": 0.0,
        "scorers": scorers,
        "steps": [],
        "notes": ["candidate trajectory missing"],
    }


def evaluate(goldens: list[dict], candidates: list[dict], *, agent: str, judge=None, seed: int = 0, command: str = "") -> dict:
    judge = judge or MockJudge()
    by_id: dict[str, dict] = {}
    for candidate in candidates:
        ident = candidate["id"]
        if ident in by_id:
            raise ValueError(f"duplicate candidate id {ident}")
        by_id[ident] = candidate
    rows = []
    for golden in goldens:
        candidate = by_id.get(golden["id"])
        if candidate is None:
            rows.append(missing_trajectory(golden))
        else:
            rows.append(score_trajectory(golden, candidate, judge))
    extra = sorted(set(by_id) - {golden["id"] for golden in goldens})
    return _run_document(rows, agent=agent, judge=judge, seed=seed, command=command, extra=extra)


def _run_document(rows: list[dict], *, agent: str, judge, seed: int, command: str, extra: list[str]) -> dict:
    from trajeval import __version__

    mean = q(sum(row["score"] for row in rows) / len(rows)) if rows else 1.0
    by_scorer = {}
    for name in WEIGHTS:
        values = [row["scorers"][name] for row in rows if name in row["scorers"]]
        if values:
            by_scorer[name] = q(sum(values) / len(values))
    return {
        "harness": "trajectory-eval-harness",
        "version": __version__,
        "agent": agent,
        "source": "synthetic",
        "seed": seed,
        "command": command,
        "judge": {"name": judge.name, "is_mock": bool(judge.is_mock)},
        "weights": dict(WEIGHTS),
        "n": len(rows),
        "mean": mean,
        "by_scorer": by_scorer,
        "extra_candidate_ids": extra,
        "trajectories": rows,
    }


def _aggregate(components: dict) -> float:
    active = {key: WEIGHTS[key] for key, value in components.items() if value is not None}
    total = sum(active.values())
    score = sum((weight / total) * components[key] for key, weight in active.items())
    return q(score)


def _score_step(index: int, golden: dict, left, right, judge, candidate: dict) -> dict:
    prompt_answer = (golden["final_answer"], candidate["final_answer"])
    if left is None:
        judgment = judge.judge_step(golden["task"], None, right, *prompt_answer)
        return _row(index, 0.0, 0.0, None, judgment, [f"extra step: {right.get('tool')}"])
    if right is None:
        schema = 0.0 if _has_schema(left) else None
        judgment = judge.judge_step(golden["task"], left, None, *prompt_answer)
        return _row(index, 0.0, 0.0, schema, judgment, [f"missing step: expected {left['tool']}"])

    tool_ok = left["tool"] == right["tool"]
    args_ok = canonical(left["arguments"]) == canonical(right["arguments"])
    obs_ok = canonical(left["observation"]) == canonical(right["observation"])
    exact = (int(tool_ok) + int(args_ok) + int(obs_ok)) / 3
    notes = []
    if not tool_ok:
        notes.append(f"tool: expected {left['tool']}, got {right['tool']}")
    if not args_ok:
        notes.append(
            f"arguments: expected {canonical(left['arguments'])}, got {canonical(right['arguments'])}"
        )
    if not obs_ok:
        notes.append(
            f"observation: expected {canonical(left['observation'])}, got {canonical(right['observation'])}"
        )
    schema = _schema_score(left, right, notes)
    judgment = judge.judge_step(golden["task"], left, right, *prompt_answer)
    if judgment.score < 1.0:
        notes.append(judgment.rationale)
    return _row(index, exact, 1.0 if tool_ok else 0.0, schema, judgment, notes)


def _schema_score(golden_step: dict, candidate_step: dict, notes: list[str]):
    checks = []
    if "argument_schema" in golden_step:
        ok, reason = validate(candidate_step["arguments"], golden_step["argument_schema"])
        checks.append(1.0 if ok else 0.0)
        if not ok:
            notes.append(f"argument schema: {reason}")
    if "observation_schema" in golden_step:
        ok, reason = validate(candidate_step["observation"], golden_step["observation_schema"])
        checks.append(1.0 if ok else 0.0)
        if not ok:
            notes.append(f"observation schema: {reason}")
    if not checks:
        return None
    return sum(checks) / len(checks)


def _has_schema(step: dict) -> bool:
    return "argument_schema" in step or "observation_schema" in step


def _row(index, exact, tool_choice, schema, judgment, notes) -> dict:
    return {
        "index": index,
        "exact": q(exact),
        "tool_choice": q(tool_choice),
        "schema": None if schema is None else q(schema),
        "judge": q(judgment.score),
        "judge_rationale": judgment.rationale,
        "notes": notes,
    }


def _public_step(row: dict) -> dict:
    public = {
        "index": row["index"],
        "exact": row["exact"],
        "tool_choice": row["tool_choice"],
        "judge": row["judge"],
    }
    if row["schema"] is not None:
        public["schema"] = row["schema"]
    if row["notes"]:
        public["notes"] = row["notes"]
    return public
