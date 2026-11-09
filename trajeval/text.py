"""Lexical comparison helpers. Not a model of meaning."""

from __future__ import annotations

import re
from collections import Counter


_TOKENS = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKENS.finditer(text)]


def token_f1(expected: str, actual: str) -> float:
    left = tokens(expected)
    right = tokens(actual)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    overlap = sum((Counter(left) & Counter(right)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(right)
    recall = overlap / len(left)
    return 2 * precision * recall / (precision + recall)


def final_answer_score(expected: str, actual: str) -> float:
    if normalize(expected) == normalize(actual):
        return 1.0
    return token_f1(expected, actual)
