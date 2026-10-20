"use client";

import Link from "next/link";
import { formatINR, formatINRShort, formatSqft } from "@/lib/format";
import { label, useMeta } from "@/lib/providers";
import type { PriceEstimate } from "@/lib/types";
import { Alert, Badge, cx } from "@/components/ui";

const POSITION_TEXT: Record<string, string> = {
  below_range: "below the indicative range",
  within_range: "within the indicative range",
  above_range: "above the indicative range",
};

/** Where the quoted price sits relative to the range, drawn on a simple bar. */
function RangeBar({ e }: { e: PriceEstimate }) {
  const low = Number(e.indicative_range_inr.low);
  const high = Number(e.indicative_range_inr.high);
  const mid = Number(e.predicted_asking_price_inr);
  const quoted = e.quoted_price_inr ? Number(e.quoted_price_inr) : null;
  const min = Math.min(low, quoted ?? low) * 0.9;
  const max = Math.max(high, quoted ?? high) * 1.1;
  const pos = (v: number) => `${((v - min) / (max - min)) * 100}%`;
  return (
    <div className="mt-4" aria-hidden="true">
      <div className="relative h-3 rounded-full bg-slate-100">
        <div className="absolute inset-y-0 rounded-full bg-brand-200" style={{ left: pos(low), width: `calc(${pos(high)} - ${pos(low)})` }} />
        <div className="absolute -top-1 h-5 w-0.5 bg-brand-700" style={{ left: pos(mid) }} />
        {quoted !== null && (
          <div className="absolute -top-1.5 h-6 w-1.5 -translate-x-1/2 rounded bg-amber-500" style={{ left: pos(quoted) }} />
        )}
      </div>
      <div className="relative mt-1 h-4 text-xs text-slate-500">
        <span className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: pos(low) }}>{formatINRShort(low)}</span>
        <span className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: pos(high) }}>{formatINRShort(high)}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        <span className="mr-1 inline-block h-2 w-3 rounded bg-brand-200 align-middle" /> indicative range
        <span className="ml-3 mr-1 inline-block h-3 w-0.5 bg-brand-700 align-middle" /> estimate
        {quoted !== null && <><span className="ml-3 mr-1 inline-block h-3 w-1.5 rounded bg-amber-500 align-middle" /> quoted price</>}
      </p>
    </div>
  );
}

export function EstimateResult({ e, compact = false }: { e: PriceEstimate; compact?: boolean }) {
  const meta = useMeta();
  const cov = Math.round(e.indicative_range_inr.measured_test_coverage * 100);
  const nominal = Math.round(e.indicative_range_inr.nominal_coverage * 100);
  const pct = e.quoted_vs_estimate_pct;
  return (
    <div className="space-y-4" data-testid="estimate-result">
      <div>
        <p className="text-sm text-slate-500">Model estimate of a typical asking price</p>
        <p className="text-3xl font-semibold text-slate-900">{formatINRShort(e.predicted_asking_price_inr)}</p>
        <p className="text-sm text-slate-600">
          Indicative range {formatINRShort(e.indicative_range_inr.low)} – {formatINRShort(e.indicative_range_inr.high)}
        </p>
        <RangeBar e={e} />
        <p className="mt-2 text-xs text-slate-500">
          The range is meant to hold about {nominal}% of asking prices; on the held-out test listings it held {cov}%.
          It comes from the model&apos;s past errors, not from a guaranteed confidence level.
          {" "}≈ {formatINR(e.predicted_price_per_sqft)} per sq ft for {formatSqft(e.normalized_area_sqft)}.
        </p>
      </div>

      {e.quoted_price_inr && pct !== null && e.quoted_position && (
        <div className={cx("rounded-lg border p-3 text-sm",
          e.quoted_position === "within_range" ? "border-slate-200 bg-slate-50" : "border-amber-300 bg-amber-50")}>
          Quoted {formatINRShort(e.quoted_price_inr)} is {Math.abs(pct).toFixed(1)}% {pct >= 0 ? "above" : "below"} the
          estimate, {POSITION_TEXT[e.quoted_position]}.
          {e.quoted_position !== "within_range" && " That is a reason to look more closely (documents, road access, exact location), not proof the price is wrong."}
        </div>
      )}

      {e.warnings.length > 0 && (
        <Alert title="Read before relying on this">
          <ul className="list-disc space-y-1 pl-5">{e.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Alert>
      )}

      {!compact && e.comparables.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-slate-900">Comparable listings (asking prices)</h3>
          <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
            {e.comparables.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm">
                <div className="min-w-0">
                  <Link href={`/properties/${c.id}`} className="font-medium text-brand-800 hover:underline">{c.title}</Link>
                  <p className="text-xs text-slate-500">
                    {c.locality}, {c.city} · {formatSqft(c.normalized_area_sqft)} · {label(meta, "PropertyType", c.property_type)}
                    {c.is_synthetic && " · synthetic"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{formatINRShort(c.asking_price_inr)}</p>
                  <p className="text-xs text-slate-500">{formatINR(c.price_per_sqft)}/sq ft</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {!compact && e.top_factors.length > 0 && (
        <details className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
          <summary className="cursor-pointer font-medium text-slate-900">What the model pays most attention to</summary>
          <p className="mt-2 text-xs text-slate-500">{e.top_factors_note}</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-slate-700">
            {e.top_factors.map((f) => <li key={f.feature}>{f.description}</li>)}
          </ol>
        </details>
      )}

      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <Badge tone="slate">{e.model.label}</Badge>
        {e.model.trained_on_synthetic && <Badge tone="amber">Trained on synthetic data</Badge>}
        <span>Version {e.model.version}</span>
      </div>
      <p className="text-xs text-slate-500">{e.disclaimer}</p>
    </div>
  );
}
