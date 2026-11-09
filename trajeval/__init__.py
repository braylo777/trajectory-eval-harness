"""Grade every step of an agent trajectory, not only the final answer.

The trajectories shipped in this repository are synthetic. The default judge
is a deterministic lexical mock. Neither one is a measurement of a production
agent or of a language model.
"""

__version__ = "0.1.0"

from trajeval.agents import RegressedAgent, SampleAgent
from trajeval.diff import diff_runs
from trajeval.gate import decide_gate
from trajeval.generate import generate
from trajeval.judge import FunctionJudge, MockJudge
from trajeval.score import evaluate, score_trajectory

__all__ = [
    "FunctionJudge",
    "MockJudge",
    "RegressedAgent",
    "SampleAgent",
    "decide_gate",
    "diff_runs",
    "evaluate",
    "generate",
    "score_trajectory",
]
