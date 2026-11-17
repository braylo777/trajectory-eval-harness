import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def reports():
    """HTML reports are generated, not committed: build them once per test session."""
    subprocess.run([sys.executable, "bench/run_eval.py"], cwd=ROOT, check=True, capture_output=True)
    return ROOT / "results"
