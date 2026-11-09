from trajeval.agents import SampleAgent
from trajeval.catalog import family_names, tasks
from trajeval.faults import CYCLE, fault_for
from trajeval.format import dump_jsonl_text, load_json, load_jsonl
from trajeval.gate import decide_gate
from trajeval.generate import generate
from trajeval.measure import build_measurements
from trajeval.schema import validate
from trajeval.score import evaluate
from trajeval.world import (
    CITIES,
    CONVERSIONS,
    EVENTS,
    EXPRESSIONS,
    FILES,
    FX,
    ORDERS,
    SEARCH,
    SKUS,
    TICKETS,
)
from trajeval import tools
from tests.helpers import ROOT


def _task_view(golden):
    return {
        "id": golden["id"],
        "task_id": golden["task_id"],
        "source": golden["source"],
        "seed": golden["seed"],
        "task": golden["task"],
        "params": golden["params"],
    }


def test_catalogue_is_a_small_set_and_expands_past_one_hundred():
    expanded = tasks(0)
    expected = (
        len(CITIES)
        + len(FILES)
        + len(EXPRESSIONS)
        + len(SEARCH)
        + len(EVENTS)
        + len(SKUS)
        + len(CONVERSIONS)
        + len(TICKETS)
        + len(ORDERS)
        + len(FX)
    )
    assert len(family_names()) == 10
    assert len(family_names()) < 15
    assert len(expanded) == expected
    assert expected >= 100
    assert {row["task_id"] for row in expanded} == set(family_names())


def test_every_generated_trajectory_is_labeled_synthetic():
    rows = generate(0)
    assert len(rows) >= 100
    assert {row["source"] for row in rows} == {"synthetic"}


def test_generator_matches_the_committed_file():
    path = ROOT / "data" / "golden.jsonl"
    fresh = generate(0)
    assert path.read_text(encoding="utf-8") == dump_jsonl_text(fresh)
    assert load_jsonl(path) == fresh


def test_example_file_is_the_first_golden_record():
    golden = (ROOT / "data" / "golden.jsonl").read_text(encoding="utf-8")
    example = (ROOT / "data" / "example.jsonl").read_text(encoding="utf-8")
    first = golden.splitlines()[0]
    assert example == first + "\n"
    loaded = load_jsonl(ROOT / "data" / "example.jsonl")
    assert loaded[0]["source"] == "synthetic"
    assert loaded[0]["id"] == "weather-000"


def test_seed_changes_wording_and_not_the_tool_trace():
    first = generate(0)
    second = generate(1)
    assert [row["id"] for row in first] == [row["id"] for row in second]
    assert [row["steps"] for row in first] == [row["steps"] for row in second]
    assert [row["final_answer"] for row in first] == [row["final_answer"] for row in second]
    assert [row["task"] for row in first] != [row["task"] for row in second]


def test_goldens_satisfy_their_own_schemas_and_are_not_errors():
    for row in load_jsonl(ROOT / "data" / "golden.jsonl"):
        assert row["steps"], row["id"]
        for index, step in enumerate(row["steps"]):
            ok, reason = validate(step["arguments"], step["argument_schema"])
            assert ok, f"{row['id']} step {index} args: {reason}"
            ok, reason = validate(step["observation"], step["observation_schema"])
            assert ok, f"{row['id']} step {index} obs: {reason}"
            assert "error" not in step["observation"]


def test_independent_world_facts_match_the_golden_file():
    assert tools.get_weather("Paris") == {"city": "Paris", "temp_c": 18, "condition": "cloudy"}
    assert tools.calculate("(18+4)*2")["value"] == 44
    assert tools.calculate("50-8*2")["value"] == 34
    assert tools.convert_units(2, "km", "m")["converted"] == 2000
    assert tools.convert_units(0, "C", "F")["converted"] == 32
    assert tools.classify_ticket("The app crashes when I export.")["queue"] == "engineering"
    assert tools.classify_ticket("How do I change my display name?")["queue"] == "support"
    paris = next(row for row in load_jsonl(ROOT / "data" / "golden.jsonl") if row["id"] == "weather-000")
    assert paris["params"] == {"city": "Paris"}
    assert paris["steps"][0]["observation"]["temp_c"] == 18
    assert paris["final_answer"] == "Paris is cloudy at 18°C."


def test_calculator_rejects_non_arithmetic():
    for expression in ("10/3", "1/0", "2+foo", "__import__('os')", "1.5", ""):
        result = tools.calculate(expression)
        assert "error" in result, expression
        assert "value" not in result


def test_sample_agent_scores_perfect_against_the_committed_golden():
    goldens = load_jsonl(ROOT / "data" / "golden.jsonl")
    candidates = [SampleAgent().run(_task_view(row)) for row in goldens]
    scored = evaluate(goldens, candidates, agent="sample")
    assert scored["mean"] == 1.0
    assert all(row["score"] == 1.0 for row in scored["trajectories"])
    baseline = load_json(ROOT / "results" / "baseline.json")
    assert baseline["mean"] == 1.0
    assert baseline["judge"]["is_mock"] is True
    assert scored["trajectories"] == baseline["trajectories"]


def test_wrong_tool_keeps_the_final_answer_and_fails_the_step():
    goldens = load_jsonl(ROOT / "data" / "golden.jsonl")
    from trajeval.agents import RegressedAgent

    ident = next(row["id"] for row in goldens if fault_for(row["id"]) == "wrong_tool")
    golden = next(row for row in goldens if row["id"] == ident)
    candidate = RegressedAgent().run(_task_view(golden))
    scored = evaluate([golden], [candidate], agent="regressed")["trajectories"][0]
    assert scored["scorers"]["final_answer"] == 1.0
    assert scored["scorers"]["tool_choice"] < 1.0
    assert scored["score"] < 1.0


def test_bad_answer_keeps_the_steps():
    goldens = load_jsonl(ROOT / "data" / "golden.jsonl")
    from trajeval.agents import RegressedAgent

    ident = next(row["id"] for row in goldens if fault_for(row["id"]) == "bad_answer")
    golden = next(row for row in goldens if row["id"] == ident)
    candidate = RegressedAgent().run(_task_view(golden))
    scored = evaluate([golden], [candidate], agent="regressed")["trajectories"][0]
    assert scored["scorers"]["tool_choice"] == 1.0
    assert scored["scorers"]["exact"] == 1.0
    assert scored["scorers"]["schema"] == 1.0
    assert scored["scorers"]["final_answer"] < 1.0


def test_every_injected_fault_occurs_and_only_ok_stays_perfect():
    goldens = load_jsonl(ROOT / "data" / "golden.jsonl")
    from trajeval.agents import RegressedAgent

    candidates = [RegressedAgent().run(_task_view(row)) for row in goldens]
    scored = evaluate(goldens, candidates, agent="regressed")
    by_fault = {name: [] for name in dict.fromkeys(CYCLE)}
    for row in scored["trajectories"]:
        by_fault[fault_for(row["id"])].append(row)
    for name, rows in by_fault.items():
        assert rows, name
        if name == "ok":
            assert all(row["score"] == 1.0 for row in rows)
        else:
            assert all(row["score"] < 1.0 for row in rows)
    assert scored["mean"] < 1.0


def test_measurements_file_matches_a_fresh_score():
    sample = load_json(ROOT / "results" / "baseline.json")
    regressed = load_json(ROOT / "results" / "regressed.json")
    sample_decision = decide_gate(sample, sample, max_drop=0.01)
    regressed_decision = decide_gate(sample, regressed, max_drop=0.01)
    live = build_measurements(
        sample,
        regressed,
        sample_gate="pass",
        regressed_gate="fail",
        sample_gate_line=sample_decision.message.splitlines()[1],
        regressed_gate_line=regressed_decision.message.splitlines()[1],
    )
    assert load_json(ROOT / "results" / "measurements.json") == live
    assert sample_decision.ok
    assert not regressed_decision.ok
    assert live["n"] >= 100
    assert live["regressed_final_answer_mean"] > live["regressed_mean"]


def test_readme_quotes_the_measurement_file():
    measured = load_json(ROOT / "results" / "measurements.json")
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "SYNTHETIC" in text
    assert measured["sample_gate_line"] in text
    assert measured["regressed_gate_line"] in text
    assert measured["sample_mean_display"] in text
    assert measured["regressed_mean_display"] in text
    assert measured["mean_drop_display"] in text
    assert measured["regressed_final_answer_mean_display"] in text
    assert str(measured["n"]) in text
    for row in measured["by_fault"]:
        fragment = (
            f"| {row['fault']} | {row['n']} | {row['mean_display']} | "
            f"{row['tool_choice_display']} | {row['exact_display']} | {row['schema_display']} | "
            f"{row['final_answer_display']} | {row['judge_display']} |"
        )
        assert fragment in text
    for name, value in measured["by_scorer_regressed_display"].items():
        assert f"| {name} | {value} |" in text
