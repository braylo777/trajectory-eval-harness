import json

import pytest

from trajeval.format import FormatError, canonical, dump_jsonl_text, load_jsonl, validate_trajectory
from tests.helpers import step, trajectory


def test_roundtrip_jsonl(tmp_path):
    row = trajectory([step("get_weather", {"city": "Paris"}, {"temp_c": 18})], answer="Paris is cloudy at 18°C.")
    path = tmp_path / "t.jsonl"
    path.write_text(dump_jsonl_text([row]), encoding="utf-8")
    assert load_jsonl(path) == [row]


def test_invalid_json_reports_the_line_number(tmp_path):
    good = dump_jsonl_text([trajectory([])]).rstrip("\n")
    path = tmp_path / "bad.jsonl"
    path.write_text(good + "\n{not json}\n", encoding="utf-8")
    with pytest.raises(FormatError, match=r":2:"):
        load_jsonl(path)


def test_missing_field_is_rejected():
    row = trajectory([])
    del row["final_answer"]
    with pytest.raises(FormatError, match="missing final_answer"):
        validate_trajectory(row)


def test_duplicate_ids_are_rejected(tmp_path):
    row = trajectory([step("get_weather", {"city": "Paris"}, {"temp_c": 18})])
    path = tmp_path / "dup.jsonl"
    path.write_text(dump_jsonl_text([row, row]), encoding="utf-8")
    with pytest.raises(FormatError, match="duplicate"):
        load_jsonl(path)


def test_unknown_field_is_rejected():
    row = trajectory([])
    row["comment"] = "nope"
    with pytest.raises(FormatError, match="unknown fields"):
        validate_trajectory(row)


def test_canonical_json_ignores_key_order():
    assert canonical({"b": 1, "a": {"d": 2, "c": 3}}) == canonical({"a": {"c": 3, "d": 2}, "b": 1})


def test_arguments_must_be_an_object():
    row = trajectory([{"tool": "get_weather", "arguments": ["Paris"], "observation": {}}])
    with pytest.raises(FormatError, match="arguments must be an object"):
        validate_trajectory(row)


def test_source_must_be_a_known_label():
    row = trajectory([])
    row["source"] = "guessed"
    with pytest.raises(FormatError, match="source"):
        validate_trajectory(row)


def test_loader_accepts_the_degree_symbol(tmp_path):
    row = trajectory([], answer="18°C")
    path = tmp_path / "deg.jsonl"
    path.write_text(dump_jsonl_text([row]), encoding="utf-8")
    loaded = load_jsonl(path)
    assert loaded[0]["final_answer"] == "18°C"
    raw = path.read_text(encoding="utf-8")
    assert "°" in raw
    assert json.loads(raw)["source"] == "synthetic"
