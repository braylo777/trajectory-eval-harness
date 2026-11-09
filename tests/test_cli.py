import subprocess
import sys

from trajeval.format import load_jsonl
from tests.helpers import ROOT


def _run(args, check=True):
    return subprocess.run(
        [sys.executable, "-m", "trajeval", *args],
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def test_cli_generate_eval_and_gate(tmp_path):
    golden = tmp_path / "golden.jsonl"
    sample = tmp_path / "sample.json"
    regressed = tmp_path / "regressed.json"
    report = tmp_path / "report.html"
    generated = _run(["generate", "--seed", "0", "--out", str(golden)])
    assert "synthetic" in generated.stdout
    rows = load_jsonl(golden)
    assert len(rows) >= 100

    scored = _run(
        ["eval", "--golden", str(golden), "--agent", "sample", "--out", str(sample), "--html", str(report)]
    )
    assert "mean 1.0000" in scored.stdout
    assert "synthetic" in report.read_text(encoding="utf-8")

    _run(["eval", "--golden", str(golden), "--agent", "regressed", "--out", str(regressed)])
    passed = _run(["gate", "--baseline", str(sample), "--current", str(sample), "--max-drop", "0.01"])
    assert passed.returncode == 0
    assert "gate: PASS" in passed.stdout

    blocked = _run(
        ["gate", "--baseline", str(sample), "--current", str(regressed), "--max-drop", "0.01"],
        check=False,
    )
    assert blocked.returncode == 1
    assert "gate: FAIL" in blocked.stdout
    assert "past the max drop" in blocked.stdout


def test_cli_rejects_agent_and_candidate_together(tmp_path):
    golden = tmp_path / "golden.jsonl"
    _run(["generate", "--seed", "0", "--out", str(golden)])
    result = _run(
        ["eval", "--golden", str(golden), "--agent", "sample", "--candidate", str(golden), "--out", str(tmp_path / "out.json")],
        check=False,
    )
    assert result.returncode == 2


def test_workflow_gates_the_sample_agent_and_requires_the_regressed_failure():
    workflow = (ROOT / ".github" / "workflows" / "eval-gate.yml").read_text(encoding="utf-8")
    script = (ROOT / "scripts" / "ci.sh").read_text(encoding="utf-8")
    assert "pull_request" in workflow
    assert "bash scripts/ci.sh" in workflow
    assert "python-version: \"3.12\"" in workflow
    assert "--agent sample" in script
    assert "--agent regressed" in script
    assert "--baseline results/baseline.json" in script
    assert "--max-drop 0.01" in script
    assert "expected the regressed agent to fail the gate" in script
