"""Straight-line distances. Coordinates in the demo data are approximate, so any
distance computed from them is approximate too and is labelled that way in the UI."""
from __future__ import annotations

import math
from decimal import Decimal

# Approximate city-centre reference points (used only for straight-line distance features).
CITY_CENTRES: dict[str, tuple[float, float]] = {
    "Hubballi": (15.3647, 75.1240),
    "Dharwad": (15.4589, 75.0078),
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_to_city_centre_km(city: str, lat: Decimal | float | None, lng: Decimal | float | None) -> float | None:
    centre = CITY_CENTRES.get(city)
    if centre is None or lat is None or lng is None:
        return None
    return round(haversine_km(float(lat), float(lng), *centre), 2)
