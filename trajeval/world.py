"""Synthetic world the sample agent reads.

Every fact here is a fixture. Currency rates are round numbers chosen so the
arithmetic is exact, not market quotes. Page text is written for the fixture.
Nothing in this module was fetched from a live system.
"""

from __future__ import annotations

# (city, temp_c, condition)
CITIES = (
    ("Paris", 18, "cloudy"),
    ("Lima", 22, "fog"),
    ("Oslo", 4, "snow"),
    ("Cairo", 31, "clear"),
    ("Tokyo", 21, "rain"),
    ("Seattle", 13, "rain"),
    ("Nairobi", 24, "clear"),
    ("Reykjavik", 7, "wind"),
    ("Lisbon", 20, "clear"),
    ("Chicago", 9, "wind"),
    ("Mumbai", 29, "humid"),
    ("Toronto", 6, "snow"),
    ("Sydney", 23, "clear"),
    ("Mexico City", 19, "cloudy"),
    ("Helsinki", 2, "snow"),
    ("Cape Town", 17, "wind"),
)

# (path, text)
FILES = (
    ("notes/readme.txt", "Ship the eval before the demo."),
    ("logs/agent.log", "step=3 tool=search status=ok"),
    ("docs/policy.md", "Refunds over 30 days need a lead."),
    ("config/limits.toml", "max_steps = 50"),
    ("data/cities.csv", "city,temp_c"),
    ("scripts/seed.py", "SEED = 0"),
    ("plans/q3.md", "Hold the frontier budget flat."),
    ("inbox/001.txt", "Customer asked for a receipt."),
    ("runbooks/oncall.md", "Page the secondary after 10 minutes."),
    ("specs/format.md", "One trajectory per JSONL line."),
    ("notes/scratch.txt", "Check schema before exact match."),
    ("archive/2024.txt", "Last year's notes stay archived."),
)

# Arithmetic only. The agent parses these; it does not call eval.
EXPRESSIONS = (
    "2+2",
    "(18+4)*2",
    "100-37",
    "8*7",
    "144/12",
    "(5+5)*(3+1)",
    "50-8*2",
    "2+3*4",
    "(2+3)*4",
    "100/5+5",
    "7-3-1",
    "2*3*4",
    "(9-3)/2",
    "10+20+30",
    "1000/25",
    "0-5+8",
)

# (query, title, url, text) — urls are on example.invalid, a reserved name.
SEARCH = (
    ("refund policy window", "Refund policy", "https://example.invalid/refunds", "Refunds are accepted within 30 days."),
    ("oncall paging rule", "Oncall runbook", "https://example.invalid/oncall", "Page the secondary after 10 minutes."),
    ("eval file format", "Trajectory format", "https://example.invalid/format", "One trajectory per JSONL line."),
    ("q3 budget note", "Q3 plan", "https://example.invalid/q3", "Hold the frontier budget flat."),
    ("seed constant", "Seed script", "https://example.invalid/seed", "The generator seed is 0."),
    ("receipt request", "Inbox note", "https://example.invalid/inbox", "Customer asked for a receipt."),
    ("city table header", "City table", "https://example.invalid/cities", "The column header is city,temp_c."),
    ("step limit config", "Limits", "https://example.invalid/limits", "The step cap in the fixture is 50."),
    ("archive policy", "Archive note", "https://example.invalid/archive", "Last year's notes stay archived."),
    ("schema check order", "Scratch note", "https://example.invalid/schema", "Check schema before exact match."),
    ("agent log line", "Agent log", "https://example.invalid/log", "step=3 tool=search status=ok"),
    ("lead approval rule", "Policy", "https://example.invalid/policy", "Refunds over 30 days need a lead."),
)

# (date, title, time)
EVENTS = (
    ("2026-03-02", "Design review", "10:00"),
    ("2026-03-03", "Vendor call", "14:30"),
    ("2026-03-04", "Office hours", "11:00"),
    ("2026-03-05", "Incident review", "16:00"),
    ("2026-03-06", "Hiring panel", "09:30"),
    ("2026-03-09", "Budget check", "13:00"),
    ("2026-03-10", "Demo dry run", "15:00"),
    ("2026-03-11", "Support sync", "10:30"),
    ("2026-03-12", "Spec reading", "14:00"),
    ("2026-03-13", "Release cut", "17:00"),
    ("2026-03-16", "Customer call", "09:00"),
    ("2026-03-17", "Retro", "16:30"),
)

# (sku, name, stock)
SKUS = (
    ("SKU-100", "Brass ruler", 42),
    ("SKU-101", "Field notebook", 120),
    ("SKU-102", "Ink bottle", 15),
    ("SKU-103", "Desk lamp", 8),
    ("SKU-104", "Linen tape", 64),
    ("SKU-105", "Cedar box", 3),
    ("SKU-106", "Graph paper", 200),
    ("SKU-107", "Steel clip", 500),
    ("SKU-108", "Cotton ribbon", 36),
    ("SKU-109", "Glass vial", 22),
    ("SKU-110", "Oak tray", 11),
    ("SKU-111", "Wool felt", 48),
    ("SKU-112", "Copper tag", 77),
    ("SKU-113", "Map tube", 9),
    ("SKU-114", "Slate board", 6),
    ("SKU-115", "Hemp twine", 140),
)

# (value, from_unit, to_unit) — every pair converts to an integer.
CONVERSIONS = (
    (2, "km", "m"),
    (5, "m", "cm"),
    (12, "cm", "mm"),
    (5000, "mm", "m"),
    (2, "kg", "g"),
    (2000, "g", "kg"),
    (4, "kg", "g"),
    (0, "C", "F"),
    (10, "C", "F"),
    (100, "C", "F"),
    (32, "F", "C"),
    (68, "F", "C"),
)

# Keyword rules live in tools.classify_ticket. Each line hits one rule.
TICKETS = (
    "The app crashes when I export.",
    "There is a bug in the total.",
    "I get an error code 500 on save.",
    "I forgot my password.",
    "I cannot login to the portal.",
    "Reset my password please.",
    "I need a refund for order A1000.",
    "Why was I charged twice?",
    "Please send the invoice again.",
    "How do I change my display name?",
    "Where is the user guide?",
    "Thanks, just leaving a note.",
)

# (order_id, status, total_usd)
ORDERS = (
    ("A1000", "shipped", 42),
    ("A1001", "processing", 18),
    ("A1002", "delivered", 75),
    ("A1003", "shipped", 10),
    ("A1004", "processing", 64),
    ("A1005", "delivered", 5),
    ("A1006", "shipped", 120),
    ("A1007", "processing", 33),
    ("A1008", "delivered", 8),
    ("A1009", "shipped", 56),
    ("A1010", "processing", 91),
    ("A1011", "delivered", 27),
)

# (amount, src, dst, numerator, denominator). amount * numerator is divisible
# by denominator. Rates are illustrative, not quotes.
FX = (
    (50, "USD", "EUR", 92, 100),
    (50, "USD", "GBP", 78, 100),
    (92, "EUR", "USD", 100, 92),
    (25, "USD", "CAD", 136, 100),
    (40, "GBP", "USD", 125, 100),
    (10, "USD", "CHF", 90, 100),
    (20, "EUR", "GBP", 85, 100),
    (80, "USD", "AUD", 150, 100),
    (15, "CAD", "USD", 80, 100),
    (30, "USD", "JPY", 15000, 100),
    (5, "GBP", "EUR", 120, 100),
    (100, "USD", "MXN", 1700, 100),
)

FAMILIES = (
    "weather",
    "file",
    "calculate",
    "search",
    "calendar",
    "inventory",
    "convert",
    "ticket",
    "order",
    "fx",
)
