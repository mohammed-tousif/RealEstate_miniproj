from decimal import Decimal

import pytest

from app.models.enums import (ConversionStatus, DocumentAvailability as A, DocumentType as D, LandClassification,
                              LayoutApprovalStatus, PropertyType as P, VerificationStatus as V)
from app.services import document_rules as rules
from app.services.area_units import acres_and_guntas, from_sqft, to_sqft


@pytest.mark.parametrize("value,unit,expected", [
    ("1", "acre", Decimal("43560.0000")),
    ("1", "gunta", Decimal("1089.0000")),
    ("40", "gunta", Decimal("43560.0000")),
    ("100", "sqm", Decimal("1076.3910")),
    ("1200", "sqft", Decimal("1200.0000")),
    ("2.25", "acre", Decimal("98010.0000")),
])
def test_to_sqft(value, unit, expected):
    assert to_sqft(value, unit) == expected


def test_round_trip_and_acre_split():
    assert from_sqft(to_sqft("3.5", "acre"), "gunta") == Decimal("140.0000")
    assert acres_and_guntas(to_sqft("90", "gunta")) == (2, Decimal("10.00"))


@pytest.mark.parametrize("bad", ["0", "-5"])
def test_rejects_non_positive_area(bad):
    with pytest.raises(ValueError):
        to_sqft(bad, "sqft")


def test_rejects_unknown_unit():
    with pytest.raises(ValueError):
        to_sqft("10", "hectare")


def test_applicability_farmland_vs_house():
    farm = rules.applicable_documents(P.agricultural_land, LandClassification.agricultural,
                                      ConversionStatus.not_applicable, LayoutApprovalStatus.not_applicable)
    assert D.dc_conversion_order not in farm and D.occupancy_certificate not in farm and D.khata not in farm
    assert D.rtc_pahani in farm
    house = rules.applicable_documents(P.independent_house, LandClassification.non_agricultural_residential,
                                       ConversionStatus.converted_claimed, LayoutApprovalStatus.not_applicable)
    assert {D.occupancy_certificate, D.commencement_certificate, D.building_plan_approval} <= set(house)
    plot = rules.applicable_documents(P.residential_plot, LandClassification.non_agricultural_residential,
                                      ConversionStatus.converted_claimed, LayoutApprovalStatus.approved_layout_claimed)
    assert D.layout_approval in plot and D.commencement_certificate not in plot


def test_completeness_weights_key_documents():
    applicable = [D.rtc_pahani, D.mutation_record]  # weights 2 and 1
    assert rules.completeness(applicable, [D.rtc_pahani]) == round(2 / 3, 4)
    assert rules.completeness(applicable, []) == 0.0
    assert rules.completeness([], [D.rtc_pahani]) == 0.0


@pytest.mark.parametrize("avail,ver,expected", [
    (A.not_provided, V.unverified, "not_provided"),
    (A.provided, V.unverified, "provided_unverified"),
    (A.provided, V.pending, "verification_pending"),
    (A.provided, V.verified, "verified"),
    (A.not_applicable, V.not_applicable, "not_applicable"),
    (A.unknown, V.unverified, "unknown"),
])
def test_display_status_six_states(avail, ver, expected):
    assert rules.display_status(avail, ver) == expected
