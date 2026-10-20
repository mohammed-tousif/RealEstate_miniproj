"""Which documents are relevant to which kind of property, and a documentation
completeness score. This is general guidance for the demo, not legal advice, and
completeness measures what the seller *declared*, never whether title is clear.
"""
from __future__ import annotations

from collections.abc import Iterable

from app.models.enums import (ConversionStatus, DocumentAvailability, DocumentType as D, LandClassification,
                              LayoutApprovalStatus, PropertyType as P, VerificationStatus)

BUILT = {P.independent_house, P.commercial_building}
PLOTS = {P.residential_plot, P.commercial_plot}

# Key documents count double in the completeness score.
KEY_DOCUMENTS = {D.rtc_pahani, D.encumbrance_certificate, D.sale_deed, D.dc_conversion_order, D.layout_approval}

DOCUMENT_GUIDANCE: dict[D, str] = {
    D.rtc_pahani: "Record of Rights, Tenancy and Crops. Shows recorded owner, extent and land use in revenue records; check it on the Karnataka Bhoomi land-records service.",
    D.mutation_record: "Shows how ownership changes were entered in revenue records over time.",
    D.encumbrance_certificate: "Lists registered transactions (sales, mortgages) on the property for a period. Having an EC does not by itself prove clear title.",
    D.khata: "Municipal property record used for tax assessment in urban areas; issued by the local body.",
    D.sale_deed: "The registered deed transferring ownership to the current seller; the chain of past deeds matters too.",
    D.dc_conversion_order: "Order permitting use of agricultural land for non-agricultural purposes (commonly called DC conversion). Needed for building on land that was agricultural.",
    D.layout_approval: "Approval of the plotted layout by the planning authority. A plot in an unapproved layout can face problems with building permission and services.",
    D.building_plan_approval: "Sanctioned building plan for a constructed property.",
    D.commencement_certificate: "Permission to begin construction, where the local authority issues one. Not a land category and not required for vacant land.",
    D.completion_certificate: "Confirms construction was completed according to the sanctioned plan, where applicable.",
    D.occupancy_certificate: "Permits occupation of a completed building, where applicable.",
    D.rera_registration: "Registration with Karnataka RERA, required for registrable real estate projects above the thresholds in the RERA Act. Individual resale plots usually are not RERA projects.",
}


def applicable_documents(property_type: P, land_classification: LandClassification,
                         conversion_status: ConversionStatus, layout_status: LayoutApprovalStatus) -> list[D]:
    docs = [D.rtc_pahani, D.mutation_record, D.encumbrance_certificate, D.sale_deed]
    if property_type != P.agricultural_land:
        docs.append(D.khata)
        # Non-agricultural use of land that was (or may have been) agricultural needs a conversion order.
        if conversion_status != ConversionStatus.not_applicable:
            docs.append(D.dc_conversion_order)
    if property_type in PLOTS and layout_status != LayoutApprovalStatus.not_applicable:
        docs.append(D.layout_approval)
    if property_type in BUILT:
        docs += [D.building_plan_approval, D.commencement_certificate, D.completion_certificate,
                 D.occupancy_certificate]
    return docs


def display_status(availability: DocumentAvailability, verification: VerificationStatus) -> str:
    """Collapse the two columns into one of the six labels shown to users."""
    if availability == DocumentAvailability.not_applicable or verification == VerificationStatus.not_applicable:
        return "not_applicable"
    if availability == DocumentAvailability.unknown:
        return "unknown"
    if availability == DocumentAvailability.not_provided:
        return "not_provided"
    if verification == VerificationStatus.verified:
        return "verified"
    if verification == VerificationStatus.pending:
        return "verification_pending"
    return "provided_unverified"


DISPLAY_LABELS = {
    "not_provided": "Not provided",
    "provided_unverified": "Provided – unverified",
    "verification_pending": "Verification pending",
    "verified": "Verified",
    "not_applicable": "Not applicable",
    "unknown": "Unknown",
}


def completeness(applicable: Iterable[D], provided: Iterable[D]) -> float:
    """Weighted share of applicable documents that were declared as provided (0..1)."""
    applicable = list(dict.fromkeys(applicable))
    if not applicable:
        return 0.0
    provided_set = set(provided)
    weight = {d: (2 if d in KEY_DOCUMENTS else 1) for d in applicable}
    total = sum(weight.values())
    got = sum(w for d, w in weight.items() if d in provided_set)
    return round(got / total, 4)
