from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def trajectory(steps, answer="ok", ident="t", task="demo task"):
    return {
        "id": ident,
        "task_id": "demo",
        "source": "synthetic",
        "task": task,
        "steps": steps,
        "final_answer": answer,
    }


def step(tool, arguments, observation, argument_schema=None, observation_schema=None):
    row = {"tool": tool, "arguments": arguments, "observation": observation}
    if argument_schema is not None:
        row["argument_schema"] = argument_schema
    if observation_schema is not None:
        row["observation_schema"] = observation_schema
    return row


def run_doc(pairs):
    """Minimal eval document. `pairs` is (id, score)."""
    return {
        "mean": round(sum(score for _, score in pairs) / len(pairs), 6),
        "trajectories": [
            {
                "id": ident,
                "task_id": "demo",
                "score": score,
                "scorers": {
                    "tool_choice": score,
                    "exact": score,
                    "schema": score,
                    "final_answer": score,
                    "judge": score,
                },
            }
            for ident, score in pairs
        ],
    }
