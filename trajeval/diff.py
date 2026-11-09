"""Diff two eval run documents.

The gate trusts per-trajectory scores, not the `mean` field. A run file whose
`mean` disagrees with its rows is reported. Baseline ids missing from the
current run are scored as 0. Ids that exist only in the current run are
listed and do not move the comparable mean.
"""

from __future__ import annotations

from trajeval.score import WEIGHTS, q


def diff_runs(baseline: dict, current: dict) -> dict:
    before = {row["id"]: row for row in baseline["trajectories"]}
    after = {row["id"]: row for row in current["trajectories"]}
    if len(before) != len(baseline["trajectories"]):
        raise ValueError("baseline run has duplicate trajectory ids")
    if len(after) != len(current["trajectories"]):
        raise ValueError("current run has duplicate trajectory ids")

    missing = sorted(set(before) - set(after))
    new = sorted(set(after) - set(before))
    regressed = []
    improved = []
    unchanged = []
    warnings = []

    for ident in sorted(set(before) & set(after)):
        record = _record(before[ident], after[ident]["score"], after[ident])
        _bucket(record, regressed, improved, unchanged)

    for ident in missing:
        record = _record(before[ident], 0.0, None)
        record["missing"] = True
        regressed.append(record)

    regressed.sort(key=lambda row: (-row["drop"], row["id"]))
    improved.sort(key=lambda row: (row["drop"], row["id"]))

    count = len(before)
    baseline_mean = q(sum(row["score"] for row in before.values()) / count) if count else 1.0
    current_scores = [after[ident]["score"] if ident in after else 0.0 for ident in before]
    current_mean = q(sum(current_scores) / count) if count else 1.0
    _warn_mean(warnings, "baseline", baseline)
    _warn_mean(warnings, "current", current)

    scorer_drop = {}
    for name in WEIGHTS:
        left = _scorer_mean(before.values(), name)
        right_rows = []
        for ident, row in before.items():
            if ident in after and name in after[ident]["scorers"]:
                right_rows.append(after[ident]["scorers"][name])
            elif name in row["scorers"]:
                right_rows.append(0.0)
        if left is None:
            continue
        right = q(sum(right_rows) / len(right_rows)) if right_rows else 0.0
        scorer_drop[name] = q(left - right)

    return {
        "baseline_mean": baseline_mean,
        "current_mean": current_mean,
        "mean_drop": q(baseline_mean - current_mean),
        "n_baseline": count,
        "n_compared": count - len(missing),
        "n_regressed": len(regressed),
        "n_improved": len(improved),
        "n_unchanged": len(unchanged),
        "missing_ids": missing,
        "new_ids": new,
        "by_scorer_drop": scorer_drop,
        "regressed": regressed,
        "improved": improved,
        "warnings": warnings,
    }


def _record(before_row: dict, after_score: float, after_row) -> dict:
    before_score = before_row["score"]
    scorer_drop = {}
    after_scorers = after_row["scorers"] if after_row else {name: 0.0 for name in WEIGHTS}
    names = set(before_row["scorers"]) | set(after_scorers)
    for name in WEIGHTS:
        if name not in names:
            continue
        scorer_drop[name] = q(before_row["scorers"].get(name, 0.0) - after_scorers.get(name, 0.0))
    return {
        "id": before_row["id"],
        "task_id": before_row.get("task_id", ""),
        "before": before_score,
        "after": q(after_score),
        "drop": q(before_score - after_score),
        "scorer_drop": scorer_drop,
    }


def _bucket(record, regressed, improved, unchanged) -> None:
    if record["drop"] > 0:
        regressed.append(record)
    elif record["drop"] < 0:
        improved.append(record)
    else:
        unchanged.append(record["id"])


def _scorer_mean(rows, name: str):
    values = [row["scorers"][name] for row in rows if name in row["scorers"]]
    if not values:
        return None
    return q(sum(values) / len(values))


def _warn_mean(warnings: list[str], label: str, run: dict) -> None:
    if "mean" not in run or not run.get("trajectories"):
        return
    rows = run["trajectories"]
    recomputed = q(sum(row["score"] for row in rows) / len(rows))
    if q(run["mean"]) != recomputed:
        warnings.append(
            f"{label} mean field is {q(run['mean'])}; trajectory scores average {recomputed}. "
            "The gate uses the trajectory scores."
        )
