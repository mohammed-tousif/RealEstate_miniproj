// The buyer's last Advisor preferences, kept in this browser so Compare can show match scores.
import type { Preferences } from "./types";

const KEY = "propwise.advisor.prefs";

export const EMPTY_PREFERENCES: Preferences = {
  min_budget: null,
  max_budget: null,
  budget_strict: true,
  property_types: [],
  types_strict: true,
  cities: [],
  locality_ids: [],
  location_strict: false,
  min_area_value: null,
  min_area_unit: "sqft",
  area_strict: false,
  objective: null,
  importance: {},
};

export function loadPreferences(): Preferences | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? { ...EMPTY_PREFERENCES, ...JSON.parse(raw) } : null;
  } catch {
    return null;
  }
}

export function storePreferences(p: Preferences | null) {
  try {
    if (p) window.localStorage.setItem(KEY, JSON.stringify(p));
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable */
  }
}
