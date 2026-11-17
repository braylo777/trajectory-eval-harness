"""What the GitHub Action runs. The sample agent must stay within the threshold.
The regressed agent must trip the gate; if it passes, this script fails."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
GATE = ["--baseline", "results/baseline.json", "--max-drop", "0.01"]


def run(*args):
    return subprocess.run([PY, *args], cwd=ROOT).returncode


def must(*args):
    if run(*args) != 0:
        sys.exit(f"failed: {' '.join(args)}")


must("-m", "pytest", "-q")
must("-m", "trajeval", "eval", "--golden", "data/golden.jsonl", "--agent", "sample", "--out", "results/ci-sample.json")
must("-m", "trajeval", "gate", *GATE, "--current", "results/ci-sample.json")
must("-m", "trajeval", "eval", "--golden", "data/golden.jsonl", "--agent", "regressed", "--out", "results/ci-regressed.json")
if run("-m", "trajeval", "gate", *GATE, "--current", "results/ci-regressed.json") == 0:
    sys.exit("expected the regressed agent to fail the gate")
print("regressed agent was blocked by the gate")
