"""Deterministic fault labels for the regressed sample agent.

The harness does not read these labels when it scores. The measurement
script recomputes them from the trajectory id so a label in the trace
cannot change the table.
"""

from __future__ import annotations

import zlib

# Three of the seven slots are "ok". crc32(id) % 7 is not a uniform split of
# this particular id set; results/measurements.json is the count.
CYCLE = ("ok", "ok", "ok", "wrong_tool", "drop_arg", "bad_answer", "drop_step")


def fault_for(trajectory_id: str) -> str:
    slot = zlib.crc32(trajectory_id.encode("utf-8")) % len(CYCLE)
    return CYCLE[slot]
