"""A small JSON Schema subset.

Supported keywords: type, required, properties, additionalProperties, items,
enum, minimum, maximum, minLength, maxLength.

`integer` does not accept booleans. `additionalProperties` is only a boolean,
not a schema. Unknown keywords are errors, so a typo does not silently pass.
"""

from __future__ import annotations

class SchemaError(ValueError):
    pass


_SUPPORTED = {
    "type",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "enum",
    "minimum",
    "maximum",
    "minLength",
    "maxLength",
}


def validate(instance, schema: dict) -> tuple[bool, str]:
    try:
        _check(instance, schema, "$")
    except SchemaError as exc:
        return False, str(exc)
    return True, ""


def _check(instance, schema: dict, path: str) -> None:
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: schema must be an object")
    unknown = sorted(set(schema) - _SUPPORTED)
    if unknown:
        raise SchemaError(f"{path}: unsupported keywords: {', '.join(unknown)}")
    if "type" in schema:
        _check_type(instance, schema["type"], path)
    if "enum" in schema and not any(_same(instance, option) for option in schema["enum"]):
        raise SchemaError(f"{path}: value not in enum")
    if _objectish(schema):
        if not isinstance(instance, dict):
            raise SchemaError(f"{path}: expected object")
        for key in schema.get("required", []):
            if key not in instance:
                raise SchemaError(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                _check(value, props[key], f"{path}.{key}")
            elif additional is False:
                raise SchemaError(f"{path}: additional property {key!r}")
    if schema.get("type") == "array" or "items" in schema:
        if not isinstance(instance, list):
            raise SchemaError(f"{path}: expected array")
        if "items" in schema:
            for index, item in enumerate(instance):
                _check(item, schema["items"], f"{path}[{index}]")
    if schema.get("type") == "string" and isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SchemaError(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            raise SchemaError(f"{path}: longer than maxLength")
    if schema.get("type") in ("integer", "number") and isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaError(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaError(f"{path}: above maximum")


def _same(left, right) -> bool:
    """Equality that does not treat True as 1."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    return left == right


def _objectish(schema: dict) -> bool:
    if schema.get("type") == "object":
        return True
    return any(key in schema for key in ("properties", "required", "additionalProperties"))


def _check_type(instance, type_name, path: str) -> None:
    if not isinstance(type_name, str):
        raise SchemaError(f"{path}: type must be a string")
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if type_name not in checks:
        raise SchemaError(f"{path}: unsupported type {type_name!r}")
    if not checks[type_name](instance):
        raise SchemaError(f"{path}: expected {type_name}")
