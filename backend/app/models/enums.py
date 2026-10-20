"""Domain enums. Values are stored as strings (with CHECK constraints) so the same
schema works on SQLite and PostgreSQL. Labels are served to the frontend through
GET /api/v1/meta/enums so names stay consistent across DB, API and UI.

Property type, land classification, conversion status, layout approval status
and document status are deliberately separate concepts (BLUEPRINT Part D).
"""
from enum import Enum


class LabelledEnum(str, Enum):
    @classmethod
    def labels(cls) -> dict[str, str]:
        return {m.value: LABELS.get((cls.__name__, m.value), m.value.replace("_", " ").capitalize()) for m in cls}


class UserRole(LabelledEnum):
    buyer = "buyer"
    seller = "seller"
    admin = "admin"


class PropertyType(LabelledEnum):
    residential_plot = "residential_plot"
    independent_house = "independent_house"
    agricultural_land = "agricultural_land"
    commercial_plot = "commercial_plot"
    commercial_building = "commercial_building"


class IntendedLandUse(LabelledEnum):
    residential = "residential"
    agricultural = "agricultural"
    commercial = "commercial"
    mixed = "mixed"
    unknown = "unknown"


class LandClassification(LabelledEnum):
    """Land use as declared (by the seller) in revenue records."""
    agricultural = "agricultural"
    non_agricultural_residential = "non_agricultural_residential"
    non_agricultural_commercial = "non_agricultural_commercial"
    unknown = "unknown"


class ConversionStatus(LabelledEnum):
    """Agricultural to non-agricultural (DC) conversion, as claimed by the seller."""
    converted_claimed = "converted_claimed"
    conversion_in_progress = "conversion_in_progress"
    not_converted = "not_converted"
    not_applicable = "not_applicable"
    unknown = "unknown"


class LayoutApprovalStatus(LabelledEnum):
    approved_layout_claimed = "approved_layout_claimed"
    unapproved_layout = "unapproved_layout"
    not_applicable = "not_applicable"
    unknown = "unknown"


class AreaUnit(LabelledEnum):
    sqft = "sqft"
    sqm = "sqm"
    gunta = "gunta"
    acre = "acre"


class RoadAccess(LabelledEnum):
    highway = "highway"
    main_road = "main_road"
    paved_internal = "paved_internal"
    unpaved = "unpaved"
    no_direct_access = "no_direct_access"
    unknown = "unknown"


class ListingStatus(LabelledEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    flagged = "flagged"
    archived = "archived"


class DocumentType(LabelledEnum):
    rtc_pahani = "rtc_pahani"
    mutation_record = "mutation_record"
    encumbrance_certificate = "encumbrance_certificate"
    khata = "khata"
    sale_deed = "sale_deed"
    dc_conversion_order = "dc_conversion_order"
    layout_approval = "layout_approval"
    building_plan_approval = "building_plan_approval"
    commencement_certificate = "commencement_certificate"
    completion_certificate = "completion_certificate"
    occupancy_certificate = "occupancy_certificate"
    rera_registration = "rera_registration"


class DocumentAvailability(LabelledEnum):
    provided = "provided"
    not_provided = "not_provided"
    not_applicable = "not_applicable"
    unknown = "unknown"


class VerificationStatus(LabelledEnum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    not_applicable = "not_applicable"


class AmenityCategory(LabelledEnum):
    education = "education"
    health = "health"
    transport = "transport"
    utilities = "utilities"
    shopping = "shopping"
    agriculture = "agriculture"
    recreation = "recreation"


LABELS: dict[tuple[str, str], str] = {
    ("PropertyType", "residential_plot"): "Residential plot",
    ("PropertyType", "independent_house"): "Independent house",
    ("PropertyType", "agricultural_land"): "Agricultural land",
    ("PropertyType", "commercial_plot"): "Commercial plot",
    ("PropertyType", "commercial_building"): "Commercial building",
    ("LandClassification", "non_agricultural_residential"): "Non-agricultural (residential)",
    ("LandClassification", "non_agricultural_commercial"): "Non-agricultural (commercial)",
    ("ConversionStatus", "converted_claimed"): "DC conversion claimed",
    ("ConversionStatus", "conversion_in_progress"): "Conversion in progress (claimed)",
    ("ConversionStatus", "not_converted"): "Not converted",
    ("LayoutApprovalStatus", "approved_layout_claimed"): "Approved layout (claimed)",
    ("LayoutApprovalStatus", "unapproved_layout"): "Unapproved layout",
    ("AreaUnit", "sqft"): "sq. ft.",
    ("AreaUnit", "sqm"): "sq. m.",
    ("AreaUnit", "gunta"): "gunta",
    ("AreaUnit", "acre"): "acre",
    ("RoadAccess", "highway"): "National/State highway frontage",
    ("RoadAccess", "main_road"): "Main road",
    ("RoadAccess", "paved_internal"): "Paved internal road",
    ("RoadAccess", "unpaved"): "Unpaved road / cart track",
    ("RoadAccess", "no_direct_access"): "No direct road access",
    ("DocumentType", "rtc_pahani"): "RTC / Pahani",
    ("DocumentType", "mutation_record"): "Mutation record",
    ("DocumentType", "encumbrance_certificate"): "Encumbrance Certificate (EC)",
    ("DocumentType", "khata"): "Khata",
    ("DocumentType", "sale_deed"): "Sale / title deed",
    ("DocumentType", "dc_conversion_order"): "DC conversion order",
    ("DocumentType", "layout_approval"): "Layout approval",
    ("DocumentType", "building_plan_approval"): "Building plan approval",
    ("DocumentType", "commencement_certificate"): "Commencement Certificate (CC)",
    ("DocumentType", "completion_certificate"): "Completion Certificate",
    ("DocumentType", "occupancy_certificate"): "Occupancy Certificate (OC)",
    ("DocumentType", "rera_registration"): "RERA registration",
    ("DocumentAvailability", "provided"): "Provided",
    ("DocumentAvailability", "not_provided"): "Not provided",
    ("VerificationStatus", "pending"): "Verification pending",
}
