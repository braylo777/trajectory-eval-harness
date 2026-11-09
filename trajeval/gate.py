"""Regression gate.

Fails when the comparable suite mean drops by more than `max_drop`.
A drop equal to the threshold passes. `past a threshold` means strictly greater.

Also fails when a baseline trajectory id is absent from the current run.
Deleting one task out of 132 drops the mean by about 0.0076, which is under
the default 0.01 threshold, so the missing-id rule is separate.

`max_task_drop`, when set, fails the gate if any single trajectory drops by
more than that amount.

The decision uses per-trajectory scores. A `mean` field that disagrees with
those scores does not decide the gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from trajeval.diff import diff_runs


@dataclass
class GateDecision:
    ok: bool
    baseline_mean: float
    current_mean: float
    mean_drop: float
    max_drop: float
    missing_ids: list
    regressed: list
    warnings: list
    message: str


def decide_gate(baseline: dict, current: dict, *, max_drop: float, max_task_drop: float | None = None) -> GateDecision:
    diff = diff_runs(baseline, current)
    reasons = []
    if diff["missing_ids"]:
        reasons.append(
            f"missing {len(diff['missing_ids'])} baseline trajectory(s): "
            + ", ".join(diff["missing_ids"])
        )
    if diff["mean_drop"] > max_drop:
        reasons.append(
            f"suite mean dropped by {diff['mean_drop']:.4f}, which is past the max drop {max_drop:.4f}"
        )
    if max_task_drop is not None:
        too_far = [row for row in diff["regressed"] if row["drop"] > max_task_drop]
        if too_far:
            reasons.append(
                f"{len(too_far)} trajectory(s) dropped by more than {max_task_drop:.4f}"
            )
    # A mean field that disagrees with the rows is a warning. The comparable
    # score already ignores that field, so the warning alone does not fail.
    ok = not reasons
    message = _message(diff, max_drop, reasons)
    return GateDecision(
        ok=ok,
        baseline_mean=diff["baseline_mean"],
        current_mean=diff["current_mean"],
        mean_drop=diff["mean_drop"],
        max_drop=max_drop,
        missing_ids=list(diff["missing_ids"]),
        regressed=list(diff["regressed"]),
        warnings=list(diff["warnings"]),
        message=message,
    )


def _message(diff: dict, max_drop: float, reasons: list[str]) -> str:
    status = "PASS" if not reasons else "FAIL"
    lines = [
        f"gate: {status}",
        (
            f"suite mean {diff['baseline_mean']:.4f} -> {diff['current_mean']:.4f} "
            f"(drop {diff['mean_drop']:.4f}, max {max_drop:.4f})"
        ),
    ]
    if diff["warnings"]:
        lines.extend(f"warning: {warning}" for warning in diff["warnings"])
    if reasons:
        lines.extend(reasons)
    if diff["regressed"]:
        lines.append(f"regressed trajectories: {len(diff['regressed'])}")
        for row in diff["regressed"][:5]:
            lines.append(
                f"  {row['id']} {row['before']:.4f} -> {row['after']:.4f} (drop {row['drop']:.4f})"
            )
    return "\n".join(lines)
