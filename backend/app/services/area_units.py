"""Indian land-area units, converted with Decimal arithmetic.

1 acre = 43,560 sq ft; 1 gunta = 1,089 sq ft (40 guntas = 1 acre); 1 sq m = 10.7639104 sq ft.
The canonical stored unit is square feet; the original value and unit are always kept too.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import AreaUnit

SQFT_PER_UNIT: dict[AreaUnit, Decimal] = {
    AreaUnit.sqft: Decimal("1"),
    AreaUnit.sqm: Decimal("10.7639104"),
    AreaUnit.gunta: Decimal("1089"),
    AreaUnit.acre: Decimal("43560"),
}

_Q = Decimal("0.0001")


def to_sqft(value: Decimal | int | float | str, unit: AreaUnit | str) -> Decimal:
    unit = AreaUnit(unit)
    v = Decimal(str(value))
    if v <= 0:
        raise ValueError("area must be greater than zero")
    return (v * SQFT_PER_UNIT[unit]).quantize(_Q, rounding=ROUND_HALF_UP)


def from_sqft(sqft: Decimal | int | float | str, unit: AreaUnit | str) -> Decimal:
    unit = AreaUnit(unit)
    return (Decimal(str(sqft)) / SQFT_PER_UNIT[unit]).quantize(_Q, rounding=ROUND_HALF_UP)


def acres_and_guntas(sqft: Decimal) -> tuple[int, Decimal]:
    """Split an area into whole acres plus remaining guntas (the way farmland is usually quoted)."""
    guntas = Decimal(sqft) / SQFT_PER_UNIT[AreaUnit.gunta]
    acres = int(guntas // 40)
    return acres, (guntas - acres * 40).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
