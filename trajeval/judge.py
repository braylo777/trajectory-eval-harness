"""Judge hook.

`MockJudge` is the default. It builds the prompt a model judge would be sent
and then scores the step with lexical overlap. It does not call a model and
does not open a network connection.

A real judge implements `judge_step` and `judge_answer` and returns
`JudgeResult` with `is_mock=False`.
"""

from __future__ import annotations

from dataclasses import dataclass

from trajeval.format import canonical
from trajeval.text import final_answer_score


@dataclass
class JudgeResult:
    score: float
    rationale: str
    is_mock: bool
    prompt: str


def build_judge_prompt(task: str, golden_step, candidate_step, golden_answer: str, candidate_answer: str) -> str:
    golden = canonical(golden_step) if golden_step is not None else "null"
    candidate = canonical(candidate_step) if candidate_step is not None else "null"
    return (
        "You are grading one step of an agent trajectory against a golden step.\n"
        "Score only what is in the step and the final answer. Do not assume facts "
        "that are not written here.\n"
        f"Task: {task}\n"
        f"Golden step: {golden}\n"
        f"Candidate step: {candidate}\n"
        f"Golden final answer: {golden_answer}\n"
        f"Candidate final answer: {candidate_answer}\n"
        "Return a score from 0 to 1 and a one-sentence reason.\n"
    )


def _jaccard(left: set, right: set) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def _keys(value) -> set:
    if isinstance(value, dict):
        return set(value)
    return set()


def _observation_overlap(golden, candidate) -> float:
    if isinstance(golden, dict) and isinstance(candidate, dict):
        return _jaccard(_keys(golden), _keys(candidate))
    return 1.0 if canonical(golden) == canonical(candidate) else 0.0


class MockJudge:
    """Deterministic stand-in for an LLM judge.

    Per aligned step, when both sides exist:

        0.5 * tool_match + 0.3 * argument_key_jaccard + 0.2 * observation_key_jaccard

    Missing or extra steps score 0. The trajectory judge score computed by the
    harness is `0.7 * mean(step scores) + 0.3 * answer score`, where the answer
    score is normalized exact match, else token F1.

    Key Jaccard ignores values on purpose. A wrong city with the right keys
    still scores well here. Exact match is a different scorer.
    """

    name = "mock"
    is_mock = True

    def judge_step(self, task: str, golden_step, candidate_step, golden_answer: str = "", candidate_answer: str = "") -> JudgeResult:
        prompt = build_judge_prompt(task, golden_step, candidate_step, golden_answer, candidate_answer)
        if golden_step is None or candidate_step is None:
            why = "missing step" if candidate_step is None else "extra step"
            return JudgeResult(0.0, f"mock judge: {why}", True, prompt)
        tool = 1.0 if golden_step.get("tool") == candidate_step.get("tool") else 0.0
        arg = _jaccard(_keys(golden_step.get("arguments")), _keys(candidate_step.get("arguments")))
        obs = _observation_overlap(golden_step.get("observation"), candidate_step.get("observation"))
        score = 0.5 * tool + 0.3 * arg + 0.2 * obs
        parts = (("arguments", arg), ("observation", obs), ("tool", tool))
        name, value = min(parts, key=lambda item: (item[1], item[0]))
        if value == 1.0:
            rationale = "mock judge: step matches"
        else:
            rationale = f"mock judge: {name} overlap {value:.2f}"
        return JudgeResult(score, rationale, True, prompt)

    def judge_answer(self, task: str, golden_answer: str, candidate_answer: str) -> JudgeResult:
        prompt = build_judge_prompt(task, None, None, golden_answer, candidate_answer)
        score = final_answer_score(golden_answer, candidate_answer)
        if score == 1.0:
            rationale = "mock judge: answer matches"
        else:
            rationale = f"mock judge: answer overlap {score:.2f}"
        return JudgeResult(score, rationale, True, prompt)


class FunctionJudge:
    """Adapter for a caller-supplied hook.

    `fn_step(task, golden_step, candidate_step) -> JudgeResult`
    `fn_answer(task, golden_answer, candidate_answer) -> JudgeResult`
    """

    is_mock = False

    def __init__(self, fn_step, fn_answer=None, name: str = "hook"):
        self.name = name
        self._fn_step = fn_step
        self._fn_answer = fn_answer

    def judge_step(self, task, golden_step, candidate_step, golden_answer: str = "", candidate_answer: str = ""):
        return self._fn_step(task, golden_step, candidate_step)

    def judge_answer(self, task, golden_answer, candidate_answer):
        if self._fn_answer is None:
            return JudgeResult(1.0, "hook: answer not scored", False, "")
        return self._fn_answer(task, golden_answer, candidate_answer)
