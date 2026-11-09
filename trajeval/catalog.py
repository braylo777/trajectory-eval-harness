"""The small task set the golden file is expanded from.

Ten families. `seed` only selects which surface wording is used. The
parameters, and therefore the tool trace, do not depend on a shuffle.
"""

from __future__ import annotations

from trajeval.world import (
    CITIES,
    CONVERSIONS,
    EVENTS,
    EXPRESSIONS,
    FAMILIES,
    FILES,
    FX,
    ORDERS,
    SEARCH,
    SKUS,
    TICKETS,
)

TEMPLATES: dict[str, tuple[str, ...]] = {
    "weather": (
        "What is the weather in {city} right now?",
        "Look up the current conditions for {city}.",
        "Tell me the temperature and conditions in {city}.",
    ),
    "file": (
        "Read {path} and quote it.",
        "What does {path} say?",
        "Open {path} and report the text.",
    ),
    "calculate": (
        "What is {expression}?",
        "Compute {expression}.",
        "Evaluate {expression} and give the number.",
    ),
    "search": (
        "Find the note about {query} and quote the page.",
        "Search for {query}, open the result, and quote it.",
        "Look up {query} and report what the page says.",
    ),
    "calendar": (
        "What is on the calendar for {date}?",
        "Which event is scheduled on {date}?",
        "Check {date} and tell me the event.",
    ),
    "inventory": (
        "How many {sku} are in stock?",
        "Look up stock for {sku}.",
        "What is the on-hand count for {sku}?",
    ),
    "convert": (
        "Convert {value} {from_unit} to {to_unit}.",
        "How many {to_unit} is {value} {from_unit}?",
        "Change {value} {from_unit} into {to_unit}.",
    ),
    "ticket": (
        "Classify this ticket and assign it: {text}",
        "Route this support message: {text}",
        "Which queue should take this, and who owns it? {text}",
    ),
    "order": (
        "What is the status of order {order_id}?",
        "Look up order {order_id}.",
        "Report the status and total for {order_id}.",
    ),
    "fx": (
        "Convert {amount} {src} to {dst}.",
        "How much is {amount} {src} in {dst} at the fixture rate?",
        "Change {amount} {src} into {dst}.",
    ),
}


def tasks(seed: int = 0) -> list[dict]:
    rows: list[dict] = []
    rows.extend(_family("weather", seed, [{"city": city} for city, _, _ in CITIES]))
    rows.extend(_family("file", seed, [{"path": path} for path, _ in FILES]))
    rows.extend(_family("calculate", seed, [{"expression": expr} for expr in EXPRESSIONS]))
    rows.extend(_family("search", seed, [{"query": query} for query, _, _, _ in SEARCH]))
    rows.extend(_family("calendar", seed, [{"date": date} for date, _, _ in EVENTS]))
    rows.extend(_family("inventory", seed, [{"sku": sku} for sku, _, _ in SKUS]))
    rows.extend(
        _family(
            "convert",
            seed,
            [{"value": value, "from_unit": src, "to_unit": dst} for value, src, dst in CONVERSIONS],
        )
    )
    rows.extend(_family("ticket", seed, [{"text": text} for text in TICKETS]))
    rows.extend(_family("order", seed, [{"order_id": order_id} for order_id, _, _ in ORDERS]))
    rows.extend(
        _family(
            "fx",
            seed,
            [{"amount": amount, "src": src, "dst": dst} for amount, src, dst, _, _ in FX],
        )
    )
    return rows


def _family(kind: str, seed: int, params_list: list[dict]) -> list[dict]:
    templates = TEMPLATES[kind]
    rows = []
    for index, params in enumerate(params_list):
        template = templates[(index + seed) % len(templates)]
        rows.append(
            {
                "id": f"{kind}-{index:03d}",
                "task_id": kind,
                "source": "synthetic",
                "seed": seed,
                "task": template.format(**params),
                "params": params,
            }
        )
    return rows


def family_names() -> tuple[str, ...]:
    return FAMILIES
