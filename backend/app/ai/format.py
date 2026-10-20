"""Indian-style money and area text for assistant answers (₹ lakh / crore, acres and guntas)."""
from __future__ import annotations

from decimal import Decimal


def _group_indian(n: int) -> str:
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + s


def inr(v: Decimal | float | int | None, exact: bool = False) -> str:
    if v is None:
        return "not available"
    x = float(v)
    if exact or abs(x) < 100_000:
        return f"₹{_group_indian(round(x))}"
    if abs(x) >= 10_000_000:
        return f"₹{x / 10_000_000:.2f}".rstrip("0").rstrip(".") + " crore"
    return f"₹{x / 100_000:.2f}".rstrip("0").rstrip(".") + " lakh"


def area_text(sqft: Decimal | float, value: Decimal | float | None = None, unit: str | None = None) -> str:
    sq = f"{_group_indian(round(float(sqft)))} sq ft"
    if unit and unit != "sqft" and value is not None:
        v = f"{float(value):.2f}".rstrip("0").rstrip(".")
        name = {"acre": "acre", "gunta": "gunta", "sqm": "sq m"}.get(unit, unit)
        return f"{v} {name} ({sq})"
    return sq
