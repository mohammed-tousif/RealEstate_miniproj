"""Reference data loaded by the seed script.

Locality names are real place names in and around Hubballi and Dharwad.
Their coordinates are rough, hand-placed approximations for map display only
(flagged `coordinates_approximate`), not surveyed boundaries or centroids.
"""
from app.models.enums import AmenityCategory as C

DISTRICT = "Dharwad"
STATE = "Karnataka"

# (locality, city, approx_lat, approx_lng, is_rural)
LOCALITIES: list[tuple[str, str, float, float, bool]] = [
    ("Vidyanagar", "Hubballi", 15.3690, 75.1290, False),
    ("Keshwapur", "Hubballi", 15.3480, 75.1390, False),
    ("Gokul Road", "Hubballi", 15.3560, 75.0960, False),
    ("Unkal", "Hubballi", 15.3860, 75.1150, False),
    ("Navanagar", "Hubballi", 15.4050, 75.0650, False),
    ("Bhairidevarkoppa", "Hubballi", 15.3930, 75.0950, False),
    ("Old Hubballi", "Hubballi", 15.3620, 75.1520, False),
    ("Gabbur", "Hubballi", 15.3290, 75.1650, True),
    ("Kusugal", "Hubballi", 15.3700, 75.2050, True),
    ("Byahatti", "Hubballi", 15.4300, 75.2000, True),
    ("Saptapur", "Dharwad", 15.4600, 75.0060, False),
    ("Kalyan Nagar", "Dharwad", 15.4520, 75.0170, False),
    ("Malmaddi", "Dharwad", 15.4480, 74.9990, False),
    ("Sattur", "Dharwad", 15.4380, 75.0340, False),
    ("Lakamanahalli", "Dharwad", 15.4740, 75.0270, False),
    ("Narayanpur", "Dharwad", 15.4680, 74.9930, False),
    ("Kelgeri", "Dharwad", 15.4560, 74.9800, True),
    ("Rayapur", "Dharwad", 15.4230, 75.0470, True),
    ("Garag", "Dharwad", 15.5650, 74.9320, True),
    ("Mugad", "Dharwad", 15.4130, 74.9200, True),
    ("Amminabhavi", "Dharwad", 15.5300, 75.0700, True),
]

# Localities that only the REAL imported listings use (scripts/build_real_listings.py). The seed
# creates them with a centre at the mean of those listings' rounded published coordinates.
# is_rural is a judgement from the place (village vs city area).
REAL_LISTING_LOCALITY_IS_RURAL: dict[str, bool] = {
    "Timmasagara": False, "Karadikop": True, "Hubballi (village not named)": False, "Tirumalkoppa": True,
    "Anchatgeri": True, "Halliyala": True, "Tegur": True, "Mangalagatti": True,
    "Manasur–Sanna Somapur": True, "Hebballi": True, "Navalur": False, "Kalakeri": True,
    "Dharwad (village not named)": False,
}

AMENITIES: list[tuple[str, str, C]] = [
    ("school", "School", C.education),
    ("college", "College", C.education),
    ("hospital", "Hospital / clinic", C.health),
    ("bus_stop", "Bus stop", C.transport),
    ("railway_station", "Railway station", C.transport),
    ("brts_stop", "BRTS stop", C.transport),
    ("municipal_water", "Municipal water supply", C.utilities),
    ("borewell", "Borewell", C.agriculture),
    ("canal_or_tank", "Canal / tank irrigation", C.agriculture),
    ("electricity", "Electricity connection", C.utilities),
    ("underground_drainage", "Underground drainage", C.utilities),
    ("market", "Market / shops", C.shopping),
    ("apmc_market", "APMC market", C.agriculture),
    ("park", "Park", C.recreation),
]
