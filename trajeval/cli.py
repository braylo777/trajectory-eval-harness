"""Command line.

    python -m trajeval generate --seed 0 --out data/golden.jsonl
    python -m trajeval eval --golden data/golden.jsonl --agent sample --out results/baseline.json
    python -m trajeval diff --baseline results/baseline.json --current results/regressed.json
    python -m trajeval gate --baseline results/baseline.json --current results/ci-sample.json --max-drop 0.01
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trajeval.agents import RegressedAgent, SampleAgent
from trajeval.diff import diff_runs
from trajeval.format import dump_json, dump_jsonl, load_json, load_jsonl
from trajeval.gate import decide_gate
from trajeval.generate import generate
from trajeval.report import render_diff_report, render_report
from trajeval.score import evaluate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trajeval", description="Grade agent trajectories step by step.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    generate_cmd = sub.add_parser("generate", help="write golden JSONL from the synthetic task set")
    generate_cmd.add_argument("--seed", type=int, default=0)
    generate_cmd.add_argument("--out", required=True)

    eval_cmd = sub.add_parser("eval", help="score a candidate JSONL file or a built-in agent")
    eval_cmd.add_argument("--golden", required=True)
    eval_cmd.add_argument("--agent", choices=("sample", "regressed"))
    eval_cmd.add_argument("--candidate")
    eval_cmd.add_argument("--out", required=True)
    eval_cmd.add_argument("--html")
    eval_cmd.add_argument("--seed", type=int, default=0)

    diff_cmd = sub.add_parser("diff", help="diff two eval JSON files")
    diff_cmd.add_argument("--baseline", required=True)
    diff_cmd.add_argument("--current", required=True)
    diff_cmd.add_argument("--out")
    diff_cmd.add_argument("--html")

    gate_cmd = sub.add_parser("gate", help="exit 1 when scores regress past a threshold")
    gate_cmd.add_argument("--baseline", required=True)
    gate_cmd.add_argument("--current", required=True)
    gate_cmd.add_argument("--max-drop", type=float, required=True)
    gate_cmd.add_argument("--max-task-drop", type=float)

    args = parser.parse_args(argv)
    if args.cmd == "generate":
        return _generate(args)
    if args.cmd == "eval":
        return _eval(args)
    if args.cmd == "diff":
        return _diff(args)
    if args.cmd == "gate":
        return _gate(args)
    parser.error(f"unknown command {args.cmd}")
    return 2


def _generate(args) -> int:
    rows = generate(args.seed)
    dump_jsonl(args.out, rows)
    print(f"wrote {len(rows)} synthetic trajectories to {args.out}")
    return 0


def _eval(args) -> int:
    if (args.agent is None) == (args.candidate is None):
        print("eval needs exactly one of --agent or --candidate", file=sys.stderr)
        return 2
    goldens = load_jsonl(args.golden)
    if args.agent:
        missing = [row["id"] for row in goldens if "params" not in row]
        if missing:
            print(
                "these goldens have no params, so the built-in agent cannot re-run them: "
                + ", ".join(missing[:8]),
                file=sys.stderr,
            )
            return 2
        agent = SampleAgent() if args.agent == "sample" else RegressedAgent()
        candidates = [agent.run(_task_view(row)) for row in goldens]
        agent_name = args.agent
        command = f"python -m trajeval eval --golden {args.golden} --agent {args.agent} --out {args.out}"
    else:
        candidates = load_jsonl(args.candidate)
        agent_name = "candidate"
        command = (
            f"python -m trajeval eval --golden {args.golden} --candidate {args.candidate} --out {args.out}"
        )
    run = evaluate(goldens, candidates, agent=agent_name, seed=args.seed, command=command)
    dump_json(args.out, run)
    print(f"mean {run['mean']:.4f} over {run['n']} trajectories -> {args.out}")
    if args.html:
        Path(args.html).write_text(render_report(run), encoding="utf-8")
        print(f"html -> {args.html}")
    return 0


def _task_view(golden: dict) -> dict:
    """Fields the scripted agents read. Schemas stay on the golden side."""
    return {
        "id": golden["id"],
        "task_id": golden["task_id"],
        "source": golden["source"],
        "seed": golden.get("seed", 0),
        "task": golden["task"],
        "params": golden["params"],
    }


def _diff(args) -> int:
    diff = diff_runs(load_json(args.baseline), load_json(args.current))
    text = (
        f"mean {diff['baseline_mean']:.4f} -> {diff['current_mean']:.4f} "
        f"(drop {diff['mean_drop']:.4f}); regressed {diff['n_regressed']}, improved {diff['n_improved']}"
    )
    print(text)
    if args.out:
        dump_json(args.out, diff)
    if args.html:
        Path(args.html).write_text(
            render_diff_report(diff, baseline_label=args.baseline, current_label=args.current),
            encoding="utf-8",
        )
    return 0


def _gate(args) -> int:
    decision = decide_gate(
        load_json(args.baseline),
        load_json(args.current),
        max_drop=args.max_drop,
        max_task_drop=args.max_task_drop,
    )
    print(decision.message)
    return 0 if decision.ok else 1
