from trajeval.schema import validate


CITY = {
    "type": "object",
    "required": ["city"],
    "properties": {"city": {"type": "string"}},
    "additionalProperties": False,
}


def test_schema_accepts_a_required_string():
    ok, reason = validate({"city": "Paris"}, CITY)
    assert ok, reason


def test_schema_rejects_a_missing_required_property():
    ok, reason = validate({}, CITY)
    assert not ok
    assert "city" in reason


def test_schema_rejects_an_additional_property():
    ok, reason = validate({"city": "Paris", "units": "c"}, CITY)
    assert not ok
    assert "units" in reason


def test_schema_enum():
    schema = {"type": "string", "enum": ["shipped", "processing"]}
    assert validate("shipped", schema)[0]
    ok, reason = validate("lost", schema)
    assert not ok
    assert "enum" in reason


def test_integer_rejects_boolean():
    ok, reason = validate(True, {"type": "integer"})
    assert not ok
    assert "integer" in reason
    assert validate(1, {"type": "integer"})[0]


def test_enum_does_not_treat_true_as_one():
    ok, _reason = validate(True, {"enum": [1]})
    assert not ok
    assert validate(1, {"enum": [1]})[0]


def test_nested_array_items():
    schema = {
        "type": "object",
        "required": ["events"],
        "additionalProperties": False,
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["title"],
                    "additionalProperties": False,
                    "properties": {"title": {"type": "string"}},
                },
            }
        },
    }
    ok, reason = validate({"events": [{"title": "Retro"}]}, schema)
    assert ok, reason
    ok, reason = validate({"events": [{"title": "Retro", "extra": 1}]}, schema)
    assert not ok


def test_unknown_keyword_is_an_error():
    ok, reason = validate("x", {"type": "string", "format": "email"})
    assert not ok
    assert "format" in reason


def test_minimum():
    assert validate(5, {"type": "integer", "minimum": 5})[0]
    assert not validate(4, {"type": "integer", "minimum": 5})[0]
