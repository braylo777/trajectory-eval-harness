"""Expand the task catalogue into golden trajectories.

The sample agent produces the trace. Schemas are attached here, and each
golden step is checked against its own schema before it is written. If the
agent and the schema drift apart, generation fails instead of shipping a
golden file that cannot score 1.
"""

from __future__ import annotations

import copy

from trajeval.agents import SampleAgent
from trajeval.catalog import tasks
from trajeval.format import validate_trajectory
from trajeval.schema import validate
from trajeval.tools import SCHEMAS


def generate(seed: int = 0) -> list[dict]:
    agent = SampleAgent()
    trajectories = []
    for task in tasks(seed):
        trajectory = agent.run(task)
        trajectory["steps"] = [_attach(step) for step in trajectory["steps"]]
        validate_trajectory(trajectory)
        _assert_self_consistent(trajectory)
        trajectories.append(trajectory)
    return trajectories


def _attach(step: dict) -> dict:
    spec = SCHEMAS.get(step["tool"])
    if spec is None:
        raise ValueError(f"no schema for tool {step['tool']}")
    attached = dict(step)
    attached["argument_schema"] = copy.deepcopy(spec["arguments"])
    attached["observation_schema"] = copy.deepcopy(spec["observation"])
    return attached


def _assert_self_consistent(trajectory: dict) -> None:
    for index, step in enumerate(trajectory["steps"]):
        ok, reason = validate(step["arguments"], step["argument_schema"])
        if not ok:
            raise ValueError(f"{trajectory['id']} step {index} arguments do not match schema: {reason}")
        ok, reason = validate(step["observation"], step["observation_schema"])
        if not ok:
            raise ValueError(f"{trajectory['id']} step {index} observation does not match schema: {reason}")
        if isinstance(step["observation"], dict) and "error" in step["observation"]:
            raise ValueError(f"{trajectory['id']} step {index} is an error observation; goldens are the success path")
