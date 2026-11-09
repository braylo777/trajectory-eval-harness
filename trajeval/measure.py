"""Build the measurement document the README quotes.

Numbers in the README are checked against this document by a test. The
document is produced by scoring the agents, not by typing a table.
"""

from __future__ import annotations

from trajeval.faults import CYCLE, fault_for
from trajeval.score import WEIGHTS


def display(value: float) -> str:
    return f"{value:.4f}"


def build_measurements(sample: dict, regressed: dict, *, sample_gate: str, regressed_gate: str, sample_gate_line: str, regressed_gate_line: str) -> dict:
    grouped: dict[str, list] = {name: [] for name in dict.fromkeys(CYCLE)}
    for row in regressed["trajectories"]:
        grouped[fault_for(row["id"])].append(row)
    by_fault = []
    for fault, rows in grouped.items():
        by_fault.append(_fault_row(fault, rows))
    final_only = _mean(row["scorers"]["final_answer"] for row in regressed["trajectories"])
    return {
        "label": "synthetic",
        "judge": "mock",
        "n": sample["n"],
        "family_count": len({row["task_id"] for row in sample["trajectories"]}),
        "sample_mean": sample["mean"],
        "sample_mean_display": display(sample["mean"]),
        "regressed_mean": regressed["mean"],
        "regressed_mean_display": display(regressed["mean"]),
        "mean_drop": round(sample["mean"] - regressed["mean"], 6),
        "mean_drop_display": display(sample["mean"] - regressed["mean"]),
        "regressed_final_answer_mean": final_only,
        "regressed_final_answer_mean_display": display(final_only),
        "by_scorer_sample": {key: sample["by_scorer"][key] for key in WEIGHTS},
        "by_scorer_regressed": {key: regressed["by_scorer"][key] for key in WEIGHTS},
        "by_scorer_regressed_display": {key: display(regressed["by_scorer"][key]) for key in WEIGHTS},
        "by_fault": by_fault,
        "gate_max_drop": 0.01,
        "sample_gate": sample_gate,
        "regressed_gate": regressed_gate,
        "sample_gate_line": sample_gate_line,
        "regressed_gate_line": regressed_gate_line,
    }


def _fault_row(fault: str, rows: list[dict]) -> dict:
    record = {
        "fault": fault,
        "n": len(rows),
        "mean": _mean(row["score"] for row in rows),
    }
    record["mean_display"] = display(record["mean"])
    for name in WEIGHTS:
        value = _mean(row["scorers"][name] for row in rows)
        record[name] = value
        record[f"{name}_display"] = display(value)
    return record


def _mean(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)
