from trajeval.judge import FunctionJudge, JudgeResult, MockJudge, build_judge_prompt
from trajeval.score import score_trajectory
from tests.helpers import step, trajectory


def test_mock_judge_is_deterministic_and_labeled_as_a_mock():
    judge = MockJudge()
    golden = {"tool": "get_weather", "arguments": {"city": "Paris"}, "observation": {"temp_c": 18}}
    first = judge.judge_step("weather?", golden, golden, "Paris", "Paris")
    second = judge.judge_step("weather?", golden, golden, "Paris", "Paris")
    assert first == second
    assert first.score == 1.0
    assert first.is_mock is True
    assert first.rationale.startswith("mock judge:")
    assert judge.is_mock is True
    assert judge.name == "mock"


def test_mock_judge_builds_a_prompt_and_does_not_claim_a_model_call():
    golden = {"tool": "get_weather", "arguments": {"city": "Paris"}, "observation": {"temp_c": 18}}
    candidate = {"tool": "search_web", "arguments": {"query": "Paris"}, "observation": {"error": "unknown"}}
    result = MockJudge().judge_step("What is the weather?", golden, candidate, "18 C", "18 C")
    assert "get_weather" in result.prompt
    assert "search_web" in result.prompt
    assert result.prompt == build_judge_prompt("What is the weather?", golden, candidate, "18 C", "18 C")
    assert "mock judge:" in result.rationale
    assert "gpt" not in result.rationale.casefold()
    assert result.score < 1.0


def test_custom_judge_hook_is_what_the_trajectory_score_uses():
    calls = {"step": 0}

    def fn_step(task, golden_step, candidate_step):
        calls["step"] += 1
        assert task == "demo task"
        assert golden_step["tool"] == "get_weather"
        return JudgeResult(0.0, "hooked", False, "")

    golden = trajectory([step("get_weather", {"city": "Paris"}, {"temp_c": 18})], answer="ok")
    scored = score_trajectory(golden, golden, judge=FunctionJudge(fn_step))
    assert calls["step"] == 1
    assert scored["scorers"]["judge"] == 0.3
    assert scored["scorers"]["tool_choice"] == 1.0
    assert scored["score"] < 1.0
