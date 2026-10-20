// Mirrors backend/app/services/document_rules.applicable_documents so the listing form only asks about
// relevant documents. The backend remains the authority and recomputes this on every request.
import type { PropertyType } from "./types";

export function applicableDocuments(type: PropertyType, conversion: string, layout: string): string[] {
  const docs = ["rtc_pahani", "mutation_record", "encumbrance_certificate", "sale_deed"];
  if (type !== "agricultural_land") {
    docs.push("khata");
    if (conversion !== "not_applicable") docs.push("dc_conversion_order");
  }
  if ((type === "residential_plot" || type === "commercial_plot") && layout !== "not_applicable") docs.push("layout_approval");
  if (type === "independent_house" || type === "commercial_building")
    docs.push("building_plan_approval", "commencement_certificate", "completion_certificate", "occupancy_certificate");
  return docs;
}

/** Sensible defaults for the classification fields when a seller picks a property type. */
export function defaultsForType(type: PropertyType) {
  switch (type) {
    case "agricultural_land":
      return { intended_land_use: "agricultural", land_classification: "agricultural", conversion_status: "not_applicable", layout_approval_status: "not_applicable" };
    case "commercial_plot":
      return { intended_land_use: "commercial", land_classification: "non_agricultural_commercial", conversion_status: "unknown", layout_approval_status: "unknown" };
    case "commercial_building":
      return { intended_land_use: "commercial", land_classification: "non_agricultural_commercial", conversion_status: "unknown", layout_approval_status: "not_applicable" };
    case "independent_house":
      return { intended_land_use: "residential", land_classification: "non_agricultural_residential", conversion_status: "unknown", layout_approval_status: "not_applicable" };
    default:
      return { intended_land_use: "residential", land_classification: "non_agricultural_residential", conversion_status: "unknown", layout_approval_status: "unknown" };
  }
}
