"use client";

import type { Recommendation } from "@/lib/types";
import { cx } from "@/components/ui";

/** Score, data coverage and the factor breakdown, all straight from the API response. */
export function ScoreBadge({ score, coverage }: { score: number; coverage: number }) {
  const tone = score >= 75 ? "bg-emerald-600" : score >= 50 ? "bg-amber-500" : "bg-slate-500";
  return (
    <div className="flex items-center gap-3">
      <div className={cx("flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-full text-white", tone)}>
        <span className="text-lg font-semibold leading-none">{Math.round(score)}</span>
        <span className="text-[10px] leading-none">/ 100</span>
      </div>
      <div className="text-xs text-slate-500">
        <p className="font-medium text-slate-700">Suitability score</p>
        <p>Based on real data for {Math.round(coverage * 100)}% of the weighting</p>
      </div>
    </div>
  );
}

export function FactorBars({ r }: { r: Recommendation }) {
  return (
    <ul className="space-y-1.5" aria-label="Score breakdown">
      {r.factors.map((f) => (
        <li key={f.factor} className="text-xs">
          <div className="flex justify-between text-slate-600">
            <span>{f.label} <span className="text-slate-400">· weight {Math.round(f.weight * 100)}%</span></span>
            <span className="font-medium text-slate-800">{Math.round(f.score * 100)}%{f.data_known < 1 ? " *" : ""}</span>
          </div>
          <div className="mt-0.5 h-1.5 rounded-full bg-slate-100">
            <div className="h-1.5 rounded-full bg-brand-600" style={{ width: `${f.score * 100}%` }} />
          </div>
        </li>
      ))}
      {r.factors.some((f) => f.data_known < 1) && <li className="text-[11px] text-slate-500">* partly based on missing data, which scores 0</li>}
    </ul>
  );
}

function List({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  if (!items.length) return null;
  return (
    <div>
      <p className={cx("text-xs font-semibold uppercase tracking-wide", tone)}>{title}</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-slate-700">{items.map((x) => <li key={x}>{x}</li>)}</ul>
    </div>
  );
}

export function Explanations({ r }: { r: Recommendation }) {
  return (
    <div className="space-y-3">
      <List title="Why it matches" items={r.reasons} tone="text-emerald-700" />
      <List title="Trade-offs" items={r.tradeoffs} tone="text-amber-700" />
      <List title="Missing information" items={r.missing_info} tone="text-slate-500" />
      <List title="Verify independently" items={r.verify_independently} tone="text-red-700" />
      {r.price_check && (
        <p className={cx("rounded-md p-2 text-xs", r.price_check.position === "within_range" ? "bg-slate-50 text-slate-600" : "bg-amber-50 text-amber-900")}>
          {r.price_check.note}
        </p>
      )}
    </div>
  );
}
