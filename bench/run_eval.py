"""Score the sample agent and the regressed agent and write results/.

This is the command behind the numbers in the README. It overwrites the
committed golden file, the baseline, and the measurement document.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trajeval.format import dump_json, dump_jsonl, load_json, load_jsonl
from trajeval.gate import decide_gate
from trajeval.measure import build_measurements


def _run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.check_call(args, cwd=ROOT)


def main() -> None:
    py = sys.executable
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "results").mkdir(parents=True, exist_ok=True)

    _run([py, "-m", "trajeval", "generate", "--seed", "0", "--out", "data/golden.jsonl"])
    rows = load_jsonl(ROOT / "data" / "golden.jsonl")
    dump_jsonl(ROOT / "data" / "example.jsonl", rows[:1])

    _run(
        [
            py, "-m", "trajeval", "eval",
            "--golden", "data/golden.jsonl",
            "--agent", "sample",
            "--out", "results/baseline.json",
            "--html", "results/sample-report.html",
        ]
    )
    _run(
        [
            py, "-m", "trajeval", "eval",
            "--golden", "data/golden.jsonl",
            "--agent", "regressed",
            "--out", "results/regressed.json",
            "--html", "results/regressed-report.html",
        ]
    )
    _run(
        [
            py, "-m", "trajeval", "diff",
            "--baseline", "results/baseline.json",
            "--current", "results/regressed.json",
            "--out", "results/diff.json",
            "--html", "results/diff-report.html",
        ]
    )

    baseline = ROOT / "results" / "baseline.json"
    regressed = ROOT / "results" / "regressed.json"
    sample_gate = decide_gate(load_json(baseline), load_json(baseline), max_drop=0.01)
    regressed_gate = decide_gate(load_json(baseline), load_json(regressed), max_drop=0.01)
    if not sample_gate.ok:
        raise SystemExit(sample_gate.message)
    if regressed_gate.ok:
        raise SystemExit("regressed agent was expected to fail the gate:\n" + regressed_gate.message)

    measurements = build_measurements(
        load_json(baseline),
        load_json(regressed),
        sample_gate="pass",
        regressed_gate="fail",
        sample_gate_line=sample_gate.message.splitlines()[1],
        regressed_gate_line=regressed_gate.message.splitlines()[1],
    )
    dump_json(ROOT / "results" / "measurements.json", measurements)
    print(sample_gate.message)
    print(regressed_gate.message)
    print(f"n={measurements['n']} sample={measurements['sample_mean_display']} regressed={measurements['regressed_mean_display']}")


if __name__ == "__main__":
    main()
