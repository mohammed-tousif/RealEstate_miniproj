// Mirrors backend/app/schemas. Money and area arrive as decimal strings.

export type PropertyType =
  | "residential_plot"
  | "independent_house"
  | "agricultural_land"
  | "commercial_plot"
  | "commercial_building";
export type AreaUnit = "sqft" | "sqm" | "gunta" | "acre";
export type RoadAccess = "highway" | "main_road" | "paved_internal" | "unpaved" | "no_direct_access" | "unknown";
export type ListingStatus = "pending" | "approved" | "rejected" | "flagged" | "archived";
export type UserRole = "buyer" | "seller" | "admin";
export type DocumentAvailability = "provided" | "not_provided" | "not_applicable" | "unknown";
export type DocumentDisplayStatus =
  | "not_provided"
  | "provided_unverified"
  | "verification_pending"
  | "verified"
  | "not_applicable"
  | "unknown";

export interface Locality {
  id: number;
  locality_name: string;
  city: string;
  district: string;
  state: string;
  center_lat: string | null;
  center_lng: string | null;
  coordinates_approximate: boolean;
}

export interface PropertySummary {
  id: string;
  title: string;
  property_type: PropertyType;
  land_classification: string;
  intended_land_use: string;
  asking_price_inr: string;
  area_value: string;
  area_unit: AreaUnit;
  normalized_area_sqft: string;
  price_per_sqft_inr: string;
  road_access: RoadAccess;
  locality: Locality;
  latitude: string | null;
  longitude: string | null;
  listing_status: ListingStatus;
  documentation_completeness: number;
  documents_provided: number;
  documents_applicable: number;
  cover_image_url: string | null;
  is_synthetic: boolean;
  data_source: string;
  source_url: string | null;
  created_at: string;
}

export interface DocumentInfo {
  document_type: string;
  label: string;
  applicable: boolean;
  availability: DocumentAvailability;
  verification_status: string;
  display_status: DocumentDisplayStatus;
  display_label: string;
  applicable_authority: string | null;
  guidance: string;
}

export interface Amenity {
  code: string;
  label: string;
  category: string;
  approx_distance_km: string | null;
  distance_is_synthetic: boolean;
}

export interface PropertyDetail extends PropertySummary {
  description: string;
  conversion_status: string;
  layout_approval_status: string;
  plot_width_ft: string | null;
  plot_length_ft: string | null;
  road_frontage_ft: string | null;
  is_corner_plot: boolean | null;
  general_address: string | null;
  coordinates_approximate: boolean;
  restriction_notes: string | null;
  additional_notes: string | null;
  relevant_authorities: string | null;
  source_retrieved_on: string | null;
  last_verified_on: string | null;
  updated_at: string;
  images: { id: number; url: string; ordering: number }[];
  documents: DocumentInfo[];
  amenities: Amenity[];
  distance_to_city_centre_km: number | null;
  data_warnings: string[];
  risk_flags: RiskFlag[];
  is_owner: boolean;
  review_reason: string | null;
}

export interface PropertyList {
  items: PropertySummary[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  applied_filters: Record<string, unknown>;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: User;
}

export interface Meta {
  enums: Record<string, Record<string, string>>;
  document_display_status: Record<string, string>;
  document_guidance: Record<string, string>;
  area_unit_sqft_factor: Record<AreaUnit, string>;
  amenities: { code: string; label: string; category: string }[];
}

export interface DocumentDeclaration {
  document_type: string;
  availability: DocumentAvailability;
}

export interface ListingInput {
  title: string;
  description: string;
  property_type: PropertyType;
  intended_land_use: string;
  land_classification: string;
  conversion_status: string;
  layout_approval_status: string;
  asking_price_inr: string;
  area_value: string;
  area_unit: AreaUnit;
  plot_width_ft: string | null;
  plot_length_ft: string | null;
  road_frontage_ft: string | null;
  road_access: RoadAccess;
  is_corner_plot: boolean | null;
  locality_id: number;
  general_address: string | null;
  latitude: string | null;
  longitude: string | null;
  restriction_notes: string | null;
  additional_notes: string | null;
  relevant_authorities: string | null;
  amenities: string[];
  documents?: DocumentDeclaration[];
  consent_to_store?: boolean;
}

export interface AdminStats {
  listings_by_status: Record<string, number>;
  listings_by_type: Record<string, number>;
  listings_by_city: Record<string, number>;
  listings_by_origin: Record<string, number>;
  users_by_role: Record<string, number>;
  total_listings: number;
}

// ---- price model (M3)

export interface PriceEstimateInput {
  property_id?: string;
  locality_id?: number;
  property_type?: PropertyType;
  area_value?: string;
  area_unit?: AreaUnit;
  land_classification?: string;
  conversion_status?: string;
  layout_approval_status?: string;
  road_access?: RoadAccess;
  road_frontage_ft?: string;
  is_corner_plot?: boolean;
  amenity_count?: number;
  asking_price_inr?: string;
}

export interface Comparable {
  id: string;
  title: string;
  property_type: PropertyType;
  locality: string;
  city: string;
  asking_price_inr: string;
  normalized_area_sqft: string;
  price_per_sqft: string;
  is_synthetic: boolean;
}

export interface PriceEstimate {
  predicted_asking_price_inr: string;
  indicative_range_inr: { low: string; high: string; nominal_coverage: number; measured_test_coverage: number; method: string };
  normalized_area_sqft: string;
  predicted_price_per_sqft: string;
  quoted_price_inr: string | null;
  quoted_vs_estimate_pct: number | null;
  quoted_position: "below_range" | "within_range" | "above_range" | null;
  comparables: Comparable[];
  top_factors: { feature: string; description: string; mae_increase_inr: string }[];
  top_factors_note: string;
  model: { name: string; label: string; version: string; trained_on_synthetic: boolean };
  warnings: string[];
  disclaimer: string;
}

export interface ModelMetrics {
  n: number;
  mae_inr: number;
  rmse_inr: number;
  r2: number;
  mape: number;
  median_ape: number;
}

export interface ModelInfo {
  price_model: null | {
    model_name: string;
    model_label: string;
    model_version: string;
    trained_at: string;
    target: string;
    trained_on_synthetic: boolean;
    dataset: { file: string; raw_rows: number; clean_rows: number; excluded_rows: number };
    split: { method: string; train: number; validation: number; test: number };
    selection: string;
    validation_metrics: Record<string, ModelMetrics>;
    test_metrics: Record<string, ModelMetrics>;
    interval: { method: string; nominal: number; measured_test_coverage: number; test_n: number };
    locality_holdout: { method: string; results: Record<string, ModelMetrics> };
    permutation_importance: { feature: string; mae_increase_inr: number }[];
    features: { name: string; description: string }[];
    caveat: string;
  };
  message: string | null;
}

// ---- recommendations (M4)

export type Importance = "very_important" | "important" | "somewhat" | "not_important";
export type Objective = "build_house" | "long_term_investment" | "farming" | "commercial_use";
export type FactorName = "budget" | "location" | "purpose" | "connectivity" | "documentation";

export interface Preferences {
  min_budget?: string | null;
  max_budget?: string | null;
  budget_strict: boolean;
  property_types: PropertyType[];
  types_strict: boolean;
  cities: ("Hubballi" | "Dharwad")[];
  locality_ids: number[];
  location_strict: boolean;
  min_area_value?: string | null;
  min_area_unit: AreaUnit;
  area_strict: boolean;
  objective?: Objective | null;
  importance: Partial<Record<FactorName, Importance>>;
}

export interface FactorScore {
  factor: FactorName;
  label: string;
  weight: number;
  score: number;
  contribution: number;
  data_known: number;
}

export interface Recommendation {
  rank: number;
  property: PropertySummary;
  score: number;
  data_coverage: number;
  factors: FactorScore[];
  reasons: string[];
  tradeoffs: string[];
  missing_info: string[];
  verify_independently: string[];
  price_check: { position: "below_range" | "within_range" | "above_range"; estimate_inr: string; note: string } | null;
}

export interface RecommendationResponse {
  results: Recommendation[];
  candidates_considered: number;
  matched: number;
  excluded: { reason: string; count: number }[];
  weights_used: Record<string, number>;
  factors_ignored: string[];
  notes: string[];
  engine_version: string;
  score_label: string;
  is_synthetic_data: boolean;
}

export interface CompareResponse {
  items: { property: PropertySummary; match: Recommendation | null; excluded_reason: string | null }[];
  warnings: string[];
  engine_version: string;
  score_label: string;
}

export interface SimilarResponse {
  items: { property: PropertySummary; distance: number; similarities: string[] }[];
  method: string;
}

export interface RecommendationConfig {
  engine_version: string;
  factors: Record<FactorName, string>;
  default_weights: Record<FactorName, number>;
  importance: Record<Importance, number>;
  road_score: Record<string, number>;
  location_scores: Record<string, number>;
  objectives: Record<Objective, string>;
  purpose_base: Record<Objective, Record<string, number>>;
  budget: { sweet_spot_from: number; non_strict_overrun: number };
  score_label: string;
}

export interface RiskFlag {
  code: string;
  severity: "high" | "medium" | "low";
  message: string;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  mode: "llm" | "basic_search";
  tool_calls: string[];
  properties: PropertySummary[];
  disclaimers: string[];
  grounded: boolean;
  notice: string | null;
}
