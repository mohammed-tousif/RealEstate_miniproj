"""Recommendation settings. These are DESIGN ASSUMPTIONS, not learned values; they are
published on the Methodology page and can be overridden per request (BLUEPRINT Part E)."""
from __future__ import annotations

ENGINE_VERSION = "weighted-v1"

FACTORS = ("budget", "location", "purpose", "connectivity", "documentation")
FACTOR_LABELS = {
    "budget": "Budget fit",
    "location": "Location",
    "purpose": "Suits your purpose",
    "connectivity": "Road access",
    "documentation": "Documents declared",
}
DEFAULT_WEIGHTS = {"budget": 30, "location": 25, "purpose": 20, "connectivity": 15, "documentation": 10}

# How much a factor counts, as chosen by the user. "not_important" removes the factor and
# the remaining weights are renormalised.
IMPORTANCE = {"very_important": 2.0, "important": 1.0, "somewhat": 0.5, "not_important": 0.0}

# Non-strict budget: listings up to 10% over the maximum are kept but scored down.
BUDGET_OVERRUN = 0.10
BUDGET_SWEET_SPOT = 0.60   # 60–100% of the maximum scores 1.0

LOCATION_SCORES = {"preferred_locality": 1.0, "preferred_city": 0.7, "other_city": 0.3}

# Ordinal road-access score. "unknown" scores 0 and is reported as missing information.
ROAD_SCORE = {"highway": 1.0, "main_road": 0.85, "paved_internal": 0.65, "unpaved": 0.35,
              "no_direct_access": 0.0, "unknown": 0.0}

OBJECTIVES = {
    "build_house": "Build a house",
    "long_term_investment": "Long-term investment",
    "farming": "Farming",
    "commercial_use": "Commercial use",
}

# Base suitability of each property type for each objective.
PURPOSE_BASE = {
    "build_house": {"residential_plot": 1.0, "independent_house": 0.8, "commercial_plot": 0.3,
                    "commercial_building": 0.1, "agricultural_land": 0.1},
    "long_term_investment": {"residential_plot": 0.85, "commercial_plot": 0.85, "agricultural_land": 0.75,
                             "independent_house": 0.6, "commercial_building": 0.6},
    "farming": {"agricultural_land": 1.0, "residential_plot": 0.05, "independent_house": 0.05,
                "commercial_plot": 0.05, "commercial_building": 0.05},
    "commercial_use": {"commercial_plot": 1.0, "commercial_building": 1.0, "residential_plot": 0.3,
                       "independent_house": 0.3, "agricultural_land": 0.05},
}

# Multipliers for the declared legal status (applied to non-agricultural property types only;
# conversion and layout approval do not apply to farmland bought for farming).
CONVERSION_MULT = {
    "strict": {"converted_claimed": 1.0, "conversion_in_progress": 0.7, "unknown": 0.7, "not_converted": 0.4,
               "not_applicable": 1.0},
    "mild": {"converted_claimed": 1.0, "conversion_in_progress": 0.85, "unknown": 0.85, "not_converted": 0.6,
             "not_applicable": 1.0},
}
LAYOUT_MULT = {
    "strict": {"approved_layout_claimed": 1.0, "unknown": 0.8, "unapproved_layout": 0.5, "not_applicable": 1.0},
    "mild": {"approved_layout_claimed": 1.0, "unknown": 0.9, "unapproved_layout": 0.7, "not_applicable": 1.0},
}
OBJECTIVE_STRICTNESS = {"build_house": "strict", "commercial_use": "strict", "long_term_investment": "mild",
                        "farming": None}
# Land classification that matches each objective (others are scored down).
EXPECTED_CLASSIFICATION = {
    "build_house": {"non_agricultural_residential"},
    "commercial_use": {"non_agricultural_commercial"},
    "farming": {"agricultural"},
    "long_term_investment": None,
}
CLASSIFICATION_MISMATCH_MULT = 0.6
# A property type the user preferred but did not require (types_strict = false).
NON_PREFERRED_TYPE_MULT = 0.5
CLASSIFICATION_UNKNOWN_MULT = 0.8

SCORE_LABEL = ("Suitability score for your stated preferences. It is not a probability of investment "
               "success and not a recommendation to buy.")
