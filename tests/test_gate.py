from trajeval.diff import diff_runs
from trajeval.gate import decide_gate
from tests.helpers import run_doc


def test_diff_lists_regressions_and_improvements():
    before = run_doc([("a", 1.0), ("b", 0.5), ("c", 1.0)])
    after = run_doc([("a", 0.25), ("b", 1.0), ("c", 1.0)])
    diff = diff_runs(before, after)
    assert [row["id"] for row in diff["regressed"]] == ["a"]
    assert [row["id"] for row in diff["improved"]] == ["b"]
    assert diff["n_unchanged"] == 1
    # (1 + 0.5 + 1) / 3 -> (0.25 + 1 + 1) / 3, rounded to 6 decimals.
    assert diff["baseline_mean"] == 0.833333
    assert diff["current_mean"] == 0.75
    assert diff["mean_drop"] == 0.083333


def test_gate_passes_when_the_drop_equals_the_threshold():
    decision = decide_gate(run_doc([("a", 1.0)]), run_doc([("a", 0.99)]), max_drop=0.01)
    assert decision.ok
    assert decision.mean_drop == 0.01
    assert decision.message.startswith("gate: PASS")


def test_gate_fails_when_the_drop_is_past_the_threshold():
    decision = decide_gate(run_doc([("a", 1.0)]), run_doc([("a", 0.5)]), max_drop=0.01)
    assert not decision.ok
    assert "past the max drop" in decision.message
    assert decision.message.startswith("gate: FAIL")


def test_gate_uses_trajectory_scores_when_the_mean_field_lies():
    baseline = run_doc([("a", 1.0)])
    honest = run_doc([("a", 1.0)])
    honest["mean"] = 0.0
    assert decide_gate(baseline, honest, max_drop=0.01).ok

    lied = run_doc([("a", 0.5)])
    lied["mean"] = 1.0
    decision = decide_gate(baseline, lied, max_drop=0.01)
    assert not decision.ok
    assert decision.mean_drop == 0.5


def test_a_dishonest_mean_warns_and_does_not_fail_a_perfect_run():
    baseline = run_doc([("a", 1.0)])
    current = run_doc([("a", 1.0)])
    current["mean"] = 0.0
    decision = decide_gate(baseline, current, max_drop=0.01)
    assert decision.ok
    assert decision.warnings
    assert "warning:" in decision.message


def test_missing_trajectory_fails_even_when_the_mean_drop_is_under_the_threshold():
    baseline = run_doc([("a", 1.0), ("b", 1.0)])
    current = run_doc([("a", 1.0)])
    # One missing row out of two is a 0.5 drop, so use a wide threshold.
    # The missing-id rule is what fails the gate, not the numeric threshold.
    decision = decide_gate(baseline, current, max_drop=0.9)
    assert not decision.ok
    assert decision.missing_ids == ["b"]
    assert decision.mean_drop == 0.5
    assert decision.mean_drop < 0.9
    assert "missing" in decision.message


def test_max_task_drop_catches_a_single_trajectory():
    baseline = run_doc([("a", 1.0), ("b", 1.0)])
    current = run_doc([("a", 0.8), ("b", 1.0)])
    # Suite drop is 0.1, under 0.2. The per-trajectory cap is 0.1, and 0.2 > 0.1.
    assert decide_gate(baseline, current, max_drop=0.2, max_task_drop=0.1).ok is False
    assert decide_gate(baseline, current, max_drop=0.2, max_task_drop=0.2).ok is True
