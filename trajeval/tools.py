"""Pure tools over the synthetic world.

`calculate` parses arithmetic. It does not call `eval`. A failed tool returns
an object with an `error` string; golden trajectories in this repo are the
success path only.
"""

from __future__ import annotations

from trajeval.world import CITIES, EVENTS, FILES, FX, ORDERS, SEARCH, SKUS

_OBJ = "object"
_STR = {"type": "string"}
_INT = {"type": "integer"}


def _object(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": _OBJ,
        "required": required if required is not None else list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


SCHEMAS: dict[str, dict[str, dict]] = {
    "get_weather": {
        "arguments": _object({"city": _STR}),
        "observation": _object({"city": _STR, "temp_c": _INT, "condition": _STR}),
    },
    "read_file": {
        "arguments": _object({"path": _STR}),
        "observation": _object({"path": _STR, "text": _STR}),
    },
    "calculate": {
        "arguments": _object({"expression": _STR}),
        "observation": _object({"expression": _STR, "value": _INT}),
    },
    "search": {
        "arguments": _object({"query": _STR}),
        "observation": _object({"title": _STR, "url": _STR}),
    },
    "open_page": {
        "arguments": _object({"url": _STR}),
        "observation": _object({"url": _STR, "title": _STR, "text": _STR}),
    },
    "list_events": {
        "arguments": _object({"date": _STR}),
        "observation": _object(
            {
                "date": _STR,
                "events": {
                    "type": "array",
                    "items": _object({"title": _STR, "time": _STR}),
                },
            }
        ),
    },
    "lookup_sku": {
        "arguments": _object({"sku": _STR}),
        "observation": _object({"sku": _STR, "name": _STR, "stock": _INT}),
    },
    "convert_units": {
        "arguments": _object({"value": _INT, "from_unit": _STR, "to_unit": _STR}),
        "observation": _object(
            {"value": _INT, "from_unit": _STR, "to_unit": _STR, "converted": _INT}
        ),
    },
    "classify_ticket": {
        "arguments": _object({"text": _STR}),
        "observation": _object(
            {
                "queue": {"type": "string", "enum": ["engineering", "access", "billing", "support"]},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
            }
        ),
    },
    "assign_ticket": {
        "arguments": _object({"queue": _STR}),
        "observation": _object({"queue": _STR, "assignee": _STR}),
    },
    "lookup_order": {
        "arguments": _object({"order_id": _STR}),
        "observation": _object(
            {
                "order_id": _STR,
                "status": {"type": "string", "enum": ["shipped", "processing", "delivered"]},
                "total_usd": _INT,
            }
        ),
    },
    "convert_currency": {
        "arguments": _object({"amount": _INT, "src": _STR, "dst": _STR}),
        "observation": _object({"amount": _INT, "src": _STR, "dst": _STR, "converted": _INT}),
    },
}


def _index(rows, key_at: int = 0):
    return {row[key_at]: row for row in rows}


_CITY = _index(CITIES)
_FILE = _index(FILES)
_EVENT = _index(EVENTS)
_SKU = _index(SKUS)
_ORDER = _index(ORDERS)
_SEARCH = {row[0]: row for row in SEARCH}
_URL = {row[2]: row for row in SEARCH}

_LENGTH = {"mm": 1, "cm": 10, "m": 1000, "km": 1_000_000}
_MASS = {"g": 1, "kg": 1000}

_PRIORITY = {"engineering": "high", "access": "high", "billing": "medium", "support": "low"}
_ASSIGNEE = {"engineering": "riley", "access": "quinn", "billing": "sam", "support": "alex"}


def get_weather(city: str) -> dict:
    row = _CITY.get(city)
    if row is None:
        return {"error": "unknown city"}
    return {"city": row[0], "temp_c": row[1], "condition": row[2]}


def read_file(path: str) -> dict:
    row = _FILE.get(path)
    if row is None:
        return {"error": "unknown path"}
    return {"path": row[0], "text": row[1]}


def search(query: str) -> dict:
    row = _SEARCH.get(query)
    if row is None:
        return {"error": "no results"}
    return {"title": row[1], "url": row[2]}


def open_page(url: str) -> dict:
    row = _URL.get(url)
    if row is None:
        return {"error": "not found"}
    return {"url": row[2], "title": row[1], "text": row[3]}


def list_events(date: str) -> dict:
    row = _EVENT.get(date)
    if row is None:
        return {"error": "no events"}
    return {"date": row[0], "events": [{"title": row[1], "time": row[2]}]}


def lookup_sku(sku: str) -> dict:
    row = _SKU.get(sku)
    if row is None:
        return {"error": "unknown sku"}
    return {"sku": row[0], "name": row[1], "stock": row[2]}


def lookup_order(order_id: str) -> dict:
    row = _ORDER.get(order_id)
    if row is None:
        return {"error": "unknown order"}
    return {"order_id": row[0], "status": row[1], "total_usd": row[2]}


def convert_units(value: int, from_unit: str, to_unit: str) -> dict:
    converted = _convert(value, from_unit, to_unit)
    if isinstance(converted, str):
        return {"error": converted}
    return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "converted": converted}


def _convert(value: int, src: str, dst: str):
    if not isinstance(value, int) or isinstance(value, bool):
        return "value must be an integer"
    if src in ("C", "F") or dst in ("C", "F"):
        return _convert_temp(value, src, dst)
    for table in (_LENGTH, _MASS):
        if src in table and dst in table:
            base = value * table[src]
            unit = table[dst]
            if base % unit != 0:
                return "result is not an integer in this fixture"
            return base // unit
    return "unknown units"


def _convert_temp(value: int, src: str, dst: str):
    if src == dst:
        return value
    if src == "C" and dst == "F":
        if (value * 9) % 5 != 0:
            return "result is not an integer in this fixture"
        return value * 9 // 5 + 32
    if src == "F" and dst == "C":
        shifted = value - 32
        if (shifted * 5) % 9 != 0:
            return "result is not an integer in this fixture"
        return shifted * 5 // 9
    return "unknown units"


def convert_currency(amount: int, src: str, dst: str) -> dict:
    match = None
    for row in FX:
        if row[0] == amount and row[1] == src and row[2] == dst:
            match = row
            break
    if match is None:
        return {"error": "no fixture rate for that pair"}
    _, _, _, num, den = match
    if den == 0 or (amount * num) % den != 0:
        return {"error": "result is not an integer in this fixture"}
    return {"amount": amount, "src": src, "dst": dst, "converted": amount * num // den}


def classify_ticket(text: str) -> dict:
    queue = _queue_for(text)
    return {"queue": queue, "priority": _PRIORITY[queue]}


def assign_ticket(queue: str) -> dict:
    assignee = _ASSIGNEE.get(queue)
    if assignee is None:
        return {"error": "unknown queue"}
    return {"queue": queue, "assignee": assignee}


def _queue_for(text: str) -> str:
    folded = text.casefold()
    # First match wins. Fixture tickets are written to hit one rule.
    rules = (
        ("engineering", ("crash", "bug", "error")),
        ("access", ("password", "login")),
        ("billing", ("refund", "charge", "invoice")),
    )
    for queue, words in rules:
        if any(word in folded for word in words):
            return queue
    return "support"


def calculate(expression: str) -> dict:
    try:
        value = _Parser(expression.replace(" ", "")).parse()
    except ValueError as exc:
        return {"expression": expression, "error": str(exc)}
    return {"expression": expression, "value": value}


class _Parser:
    def __init__(self, source: str):
        self.source = source
        self.index = 0

    def parse(self) -> int:
        if self.source == "":
            raise ValueError("empty expression")
        value = self._expr()
        if self.index != len(self.source):
            raise ValueError("trailing input")
        return value

    def _expr(self) -> int:
        value = self._term()
        while self._peek() in {"+", "-"}:
            op = self._pop()
            right = self._term()
            value = value + right if op == "+" else value - right
        return value

    def _term(self) -> int:
        value = self._unary()
        while self._peek() in {"*", "/"}:
            op = self._pop()
            right = self._unary()
            if op == "*":
                value *= right
            else:
                if right == 0:
                    raise ValueError("division by zero")
                if value % right != 0:
                    raise ValueError("non-integer division")
                value //= right
        return value

    def _unary(self) -> int:
        if self._peek() == "-":
            self._pop()
            return -self._unary()
        return self._primary()

    def _primary(self) -> int:
        if self._peek() == "(":
            self._pop()
            value = self._expr()
            if self._peek() != ")":
                raise ValueError("missing closing parenthesis")
            self._pop()
            return value
        return self._number()

    def _number(self) -> int:
        start = self.index
        while self._peek().isdigit():
            self.index += 1
        if self.index == start:
            raise ValueError("expected a number")
        return int(self.source[start : self.index])

    def _peek(self) -> str:
        if self.index >= len(self.source):
            return ""
        return self.source[self.index]

    def _pop(self) -> str:
        char = self._peek()
        self.index += 1
        return char

