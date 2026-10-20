// Indian number and unit formatting helpers (pure functions, unit-tested).

const SQFT_PER: Record<string, number> = { sqft: 1, sqm: 10.7639104, gunta: 1089, acre: 43560 };

/** ₹ with Indian digit grouping, e.g. 1840000 -> "₹18,40,000". */
export function formatINR(value: string | number): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

/** Compact lakh/crore form, e.g. 1840000 -> "₹18.4 lakh", 32500000 -> "₹3.25 crore". */
export function formatINRShort(value: string | number): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  if (n >= 1e7) return `₹${trim(n / 1e7, 2)} crore`;
  if (n >= 1e5) return `₹${trim(n / 1e5, 2)} lakh`;
  return formatINR(n);
}

function trim(x: number, digits: number): string {
  return x.toFixed(digits).replace(/\.?0+$/, "");
}

export const UNIT_LABEL: Record<string, string> = { sqft: "sq ft", sqm: "sq m", gunta: "gunta", acre: "acre" };

export function formatArea(value: string | number, unit: string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  const label = UNIT_LABEL[unit] ?? unit;
  const plural = (unit === "acre" || unit === "gunta") && n !== 1 ? "s" : "";
  return `${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })} ${label}${plural}`;
}

/** Farmland is usually quoted as "2 acres 10 guntas". */
export function acresAndGuntas(sqft: string | number): string {
  const guntas = Number(sqft) / 1089;
  const acres = Math.floor(guntas / 40 + 1e-9);
  const rest = Math.round((guntas - acres * 40) * 100) / 100;
  const parts = [];
  if (acres) parts.push(`${acres} acre${acres === 1 ? "" : "s"}`);
  if (rest || !acres) parts.push(`${rest} gunta${rest === 1 ? "" : "s"}`);
  return parts.join(" ");
}

export function toSqft(value: number, unit: string): number {
  return value * (SQFT_PER[unit] ?? NaN);
}

export function formatSqft(value: string | number): string {
  return `${Math.round(Number(value)).toLocaleString("en-IN")} sq ft`;
}

/** Parses "25 lakh", "1.2 crore", "2500000" -> rupees. Returns null if not understood. */
export function parseINR(input: string): number | null {
  const s = input.trim().toLowerCase().replace(/[₹,\s]/g, "");
  const m = s.match(/^(\d+(?:\.\d+)?)(lakh|lakhs|lac|l|crore|crores|cr)?$/);
  if (!m) return null;
  const n = Number(m[1]);
  const unit = m[2] ?? "";
  if (unit.startsWith("c")) return Math.round(n * 1e7);
  if (unit.startsWith("l")) return Math.round(n * 1e5);
  return Math.round(n);
}

export function percent(x: number): string {
  return `${Math.round(x * 100)}%`;
}

export function humanize(code: string, labels?: Record<string, string>): string {
  if (labels && labels[code]) return labels[code];
  const s = code.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function formatDate(iso: string): string {
  // SQLite returns timestamps without a zone; treat them as UTC.
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
