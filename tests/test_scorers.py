from trajeval.score import WEIGHTS, score_trajectory
from tests.helpers import step, trajectory


def _pair(tool="get_weather", arguments=None, observation=None, answer="Paris is cloudy at 18°C."):
    arguments = {"city": "Paris"} if arguments is None else arguments
    observation = {"temp_c": 18} if observation is None else observation
    row = trajectory([step(tool, arguments, observation)], answer=answer)
    return row


def test_exact_match_is_perfect_and_ignores_argument_key_order():
    golden = _pair(arguments={"city": "Paris", "units": "c"})
    candidate = _pair(arguments={"units": "c", "city": "Paris"})
    scored = score_trajectory(golden, candidate)
    assert scored["score"] == 1.0
    assert scored["scorers"]["exact"] == 1.0
    assert scored["notes"] == []


def test_wrong_arguments_fail_exact_match():
    scored = score_trajectory(_pair(), _pair(arguments={"city": "Lima"}))
    assert scored["scorers"]["exact"] < 1.0
    assert scored["scorers"]["tool_choice"] == 1.0
    assert any("arguments" in note for note in scored["notes"])


def test_wrong_observation_fails_exact_match():
    scored = score_trajectory(_pair(), _pair(observation={"temp_c": 0}))
    assert scored["scorers"]["exact"] < 1.0
    assert scored["scorers"]["tool_choice"] == 1.0


def test_wrong_tool_fails_tool_choice_and_exact():
    scored = score_trajectory(_pair(), _pair(tool="search_web"))
    assert scored["scorers"]["tool_choice"] == 0.0
    assert scored["scorers"]["exact"] < 1.0


def test_missing_step_scores_zero_on_the_step_scorers():
    golden = _pair()
    candidate = trajectory([], answer=golden["final_answer"])
    scored = score_trajectory(golden, candidate)
    assert scored["scorers"]["tool_choice"] == 0.0
    assert scored["scorers"]["exact"] == 0.0
    assert scored["scorers"]["final_answer"] == 1.0


def test_extra_step_penalizes_tool_choice_and_not_the_schema_denominator():
    schema = {
        "type": "object",
        "required": ["city"],
        "properties": {"city": {"type": "string"}},
        "additionalProperties": False,
    }
    golden_step = step("get_weather", {"city": "Paris"}, {"temp_c": 18}, argument_schema=schema)
    extra = step("search", {"query": "x"}, {"error": "no"})
    golden = trajectory([golden_step], answer="ok")
    candidate = trajectory(
        [step("get_weather", {"city": "Paris"}, {"temp_c": 18}), extra],
        answer="ok",
    )
    scored = score_trajectory(golden, candidate)
    assert scored["scorers"]["tool_choice"] == 0.5
    # Schema is averaged over golden steps only. The extra step is not a schema failure.
    assert scored["scorers"]["schema"] == 1.0
    assert "schema" not in scored["steps"][1]


def test_final_answer_ignores_case_and_whitespace():
    golden = _pair(answer="Paris is cloudy")
    candidate = _pair(answer="  paris   is cloudy  ")
    assert score_trajectory(golden, candidate)["scorers"]["final_answer"] == 1.0


def test_final_answer_partial_overlap_is_token_f1_not_zero_or_one():
    golden = _pair(answer="Paris is cloudy at 18 C")
    candidate = _pair(answer="Paris is clear")
    score = score_trajectory(golden, candidate)["scorers"]["final_answer"]
    assert 0.0 < score < 1.0


def test_index_alignment_does_not_shift_a_correct_later_step():
    good = step("get_weather", {"city": "Paris"}, {"temp_c": 18})
    golden = trajectory([good], answer="ok")
    candidate = trajectory(
        [step("search_web", {"query": "weather"}, {"error": "unknown"}), good],
        answer="ok",
    )
    scored = score_trajectory(golden, candidate)
    assert scored["scorers"]["tool_choice"] == 0.0
    assert scored["steps"][0]["tool_choice"] == 0.0


def test_weights_sum_to_one_and_a_schemaless_perfect_trace_scores_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    scored = score_trajectory(_pair(), _pair())
    assert "schema" not in scored["scorers"]
    assert scored["score"] == 1.0


def test_schema_failure_lowers_the_trajectory_below_the_schemaless_score():
    schema = {
        "type": "object",
        "required": ["city"],
        "properties": {"city": {"type": "string"}},
        "additionalProperties": False,
    }
    golden = trajectory(
        [step("get_weather", {"city": "Paris"}, {"temp_c": 18}, argument_schema=schema)],
        answer="ok",
    )
    candidate = trajectory(
        [step("get_weather", {}, {"temp_c": 18})],
        answer="ok",
    )
    scored = score_trajectory(golden, candidate)
    assert scored["scorers"]["schema"] == 0.0
    assert scored["score"] < 1.0


def test_unscored_metadata_does_not_change_the_score():
    golden = _pair()
    candidate = _pair()
    candidate["meta"] = {"fault": "wrong_tool"}
    candidate["steps"][0]["thought"] = "this is not graded"
    assert score_trajectory(golden, candidate)["score"] == score_trajectory(golden, _pair())["score"]
