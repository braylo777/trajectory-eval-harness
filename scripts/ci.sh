#!/usr/bin/env bash
# What the GitHub Action runs. The sample agent must stay within the threshold.
# The regressed agent must trip the gate; if it passes, this script fails.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pytest -q

python3 -m trajeval eval \
  --golden data/golden.jsonl \
  --agent sample \
  --out results/ci-sample.json

python3 -m trajeval gate \
  --baseline results/baseline.json \
  --current results/ci-sample.json \
  --max-drop 0.01

python3 -m trajeval eval \
  --golden data/golden.jsonl \
  --agent regressed \
  --out results/ci-regressed.json

if python3 -m trajeval gate \
  --baseline results/baseline.json \
  --current results/ci-regressed.json \
  --max-drop 0.01
then
  echo "expected the regressed agent to fail the gate" >&2
  exit 1
fi

echo "regressed agent was blocked by the gate"
