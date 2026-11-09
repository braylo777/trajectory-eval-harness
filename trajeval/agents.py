"""Scripted agents.

`SampleAgent` follows the reference policy. `RegressedAgent` runs that policy
and then edits the recorded trajectory. The edit is the regression. Faults
other than `bad_answer` keep the original final answer, so a grader that only
reads the answer misses them.
"""

from __future__ import annotations

import copy

from trajeval import tools
from trajeval.faults import fault_for


class SampleAgent:
    name = "sample"

    def run(self, task: dict) -> dict:
        kind = task["task_id"]
        handler = {
            "weather": _weather,
            "file": _file,
            "calculate": _calculate,
            "search": _search,
            "calendar": _calendar,
            "inventory": _inventory,
            "convert": _convert,
            "ticket": _ticket,
            "order": _order,
            "fx": _fx,
        }[kind]
        steps, answer = handler(task["params"])
        return {
            "id": task["id"],
            "task_id": task["task_id"],
            "source": "synthetic",
            "seed": task["seed"],
            "task": task["task"],
            "params": task["params"],
            "steps": steps,
            "final_answer": answer,
        }


class RegressedAgent:
    """Sample agent with a deterministic edit applied to the trace.

    The edit is chosen from the trajectory id (see `fault_for`). This class
    does not write the fault name into the trajectory.
    """

    name = "regressed"

    def run(self, task: dict) -> dict:
        trajectory = copy.deepcopy(SampleAgent().run(task))
        return _apply_fault(trajectory, fault_for(task["id"]), task)


def _step(tool: str, arguments: dict, observation: dict) -> dict:
    return {"tool": tool, "arguments": arguments, "observation": observation}


def _weather(params: dict):
    obs = tools.get_weather(params["city"])
    answer = f"{obs['city']} is {obs['condition']} at {obs['temp_c']}°C."
    return [_step("get_weather", {"city": params["city"]}, obs)], answer


def _file(params: dict):
    obs = tools.read_file(params["path"])
    answer = f"{params['path']} says: {obs['text']}"
    return [_step("read_file", {"path": params["path"]}, obs)], answer


def _calculate(params: dict):
    obs = tools.calculate(params["expression"])
    answer = f"{params['expression']} = {obs['value']}"
    return [_step("calculate", {"expression": params["expression"]}, obs)], answer


def _search(params: dict):
    found = tools.search(params["query"])
    page = tools.open_page(found["url"])
    steps = [
        _step("search", {"query": params["query"]}, found),
        _step("open_page", {"url": found["url"]}, page),
    ]
    answer = f"{page['title']}: {page['text']}"
    return steps, answer


def _calendar(params: dict):
    obs = tools.list_events(params["date"])
    event = obs["events"][0]
    answer = f"On {params['date']}, {event['title']} at {event['time']}."
    return [_step("list_events", {"date": params["date"]}, obs)], answer


def _inventory(params: dict):
    obs = tools.lookup_sku(params["sku"])
    answer = f"{obs['sku']} ({obs['name']}) has {obs['stock']} in stock."
    return [_step("lookup_sku", {"sku": params["sku"]}, obs)], answer


def _convert(params: dict):
    obs = tools.convert_units(params["value"], params["from_unit"], params["to_unit"])
    answer = f"{params['value']} {params['from_unit']} = {obs['converted']} {params['to_unit']}."
    return [
        _step(
            "convert_units",
            {"value": params["value"], "from_unit": params["from_unit"], "to_unit": params["to_unit"]},
            obs,
        )
    ], answer


def _ticket(params: dict):
    classified = tools.classify_ticket(params["text"])
    assigned = tools.assign_ticket(classified["queue"])
    steps = [
        _step("classify_ticket", {"text": params["text"]}, classified),
        _step("assign_ticket", {"queue": classified["queue"]}, assigned),
    ]
    answer = f"Queued to {assigned['queue']} and assigned to {assigned['assignee']}."
    return steps, answer


def _order(params: dict):
    obs = tools.lookup_order(params["order_id"])
    answer = f"Order {obs['order_id']} is {obs['status']}; total ${obs['total_usd']}."
    return [_step("lookup_order", {"order_id": params["order_id"]}, obs)], answer


def _fx(params: dict):
    obs = tools.convert_currency(params["amount"], params["src"], params["dst"])
    answer = f"{params['amount']} {params['src']} = {obs['converted']} {params['dst']}."
    return [
        _step(
            "convert_currency",
            {"amount": params["amount"], "src": params["src"], "dst": params["dst"]},
            obs,
        )
    ], answer


def _apply_fault(trajectory: dict, fault: str, task: dict) -> dict:
    if fault == "ok" or not trajectory["steps"]:
        return trajectory
    if fault == "wrong_tool":
        trajectory["steps"][0] = {
            "tool": "search_web",
            "arguments": {"query": task["task"]},
            "observation": {"error": "unknown tool"},
        }
        return trajectory
    if fault == "drop_arg":
        arguments = dict(trajectory["steps"][0]["arguments"])
        if arguments:
            arguments.pop(sorted(arguments)[0])
        trajectory["steps"][0]["arguments"] = arguments
        trajectory["steps"][0]["observation"] = {"error": "missing required argument"}
        return trajectory
    if fault == "bad_answer":
        trajectory["final_answer"] = "Unable to complete the request."
        return trajectory
    if fault == "drop_step":
        trajectory["steps"] = trajectory["steps"][:-1]
        return trajectory
    raise ValueError(f"unknown fault {fault}")
