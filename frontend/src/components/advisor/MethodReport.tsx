"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { label, useMeta } from "@/lib/providers";
import type { RecommendationConfig } from "@/lib/types";
import { Skeleton } from "@/components/ui";

const IMPORTANCE_TEXT: Record<string, string> = { very_important: "Very important", important: "Important", somewhat: "Somewhat", not_important: "Doesn't matter" };

export function MethodReport() {
  const meta = useMeta();
  const [c, setC] = useState<RecommendationConfig | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { api.recommendationConfig().then(setC).catch(() => setFailed(true)); }, []);
  if (failed) return <p>The scoring configuration could not be loaded from the server.</p>;
  if (!c) return <Skeleton className="h-40 w-full" />;
  const types = Object.keys(c.purpose_base.build_house);
  return (
    <div className="space-y-3">
      <p>
        Recommendations come from a transparent weighted scoring rule (engine <code>{c.engine_version}</code>), not a trained model.
        It runs in three steps:
      </p>
      <ol className="list-decimal space-y-1 pl-5">
        <li><strong>Filter.</strong> Only approved listings are considered. A requirement you mark strict (budget, type, area, location) removes listings that fail it, and the page says how many were removed and why. A non-strict budget allows up to {Math.round(c.budget.non_strict_overrun * 100)}% over.</li>
        <li><strong>Score.</strong> Each listing gets a 0–1 score on five factors, multiplied by its weight. The total is out of 100.</li>
        <li><strong>Explain.</strong> Reasons, trade-offs and missing information are generated from the same numbers, so the text always matches the score.</li>
      </ol>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-sm">
          <caption className="mb-1 text-left text-xs text-slate-500">Default weights (before your importance settings)</caption>
          <tbody>
            {Object.entries(c.default_weights).map(([f, w]) => (
              <tr key={f} className="border-t border-slate-100"><td className="py-1 pr-3">{c.factors[f as keyof typeof c.factors]}</td><td>{w}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        Your importance setting multiplies each weight ({Object.entries(c.importance).map(([k, v]) => `${IMPORTANCE_TEXT[k]} ×${v}`).join(", ")}), and the
        weights are rescaled to add up to 100. A factor you did not state a preference for (for example, location when no city is chosen) is left out rather than scored.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li><strong>Budget:</strong> full marks between {Math.round(c.budget.sweet_spot_from * 100)}% and 100% of your maximum; lower for listings far below it (often smaller or less suitable) and for any allowed overrun.</li>
        <li><strong>Location:</strong> preferred locality {c.location_scores.preferred_locality}; another locality in a preferred city {c.location_scores.preferred_city} (or {c.location_scores.preferred_locality} if you chose only cities); elsewhere {c.location_scores.other_city}.</li>
        <li><strong>Road access:</strong> {Object.entries(c.road_score).map(([k, v]) => `${label(meta, "RoadAccess", k)} ${v}`).join(", ")}. Unknown scores 0 and is shown as missing information.</li>
        <li><strong>Documents declared:</strong> the listing&apos;s documentation completeness. This counts declared documents only; nothing is verified.</li>
        <li><strong>Purpose:</strong> how well the property type suits your objective (table below), reduced when the land classification, conversion or layout approval does not fit (for example, agricultural land for building a house without a declared conversion).</li>
      </ul>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <caption className="mb-1 text-left text-xs text-slate-500">Purpose base scores by property type</caption>
          <thead className="text-xs uppercase text-slate-500"><tr><th className="py-1 pr-3">Objective</th>{types.map((t) => <th key={t} className="pr-3">{label(meta, "PropertyType", t)}</th>)}</tr></thead>
          <tbody>
            {Object.entries(c.purpose_base).map(([o, row]) => (
              <tr key={o} className="border-t border-slate-100"><td className="py-1 pr-3">{c.objectives[o as keyof typeof c.objectives]}</td>{types.map((t) => <td key={t} className="pr-3">{row[t]}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        Ties are broken by documents declared, then lower price. Missing data never earns points, and each result reports how much of its score rests on known fields.
        &ldquo;Similar listings&rdquo; on a property page use k-nearest neighbours over standardised price, area, location, road access and documents, with property type weighted heavily.
      </p>
      <p>
        <strong>How it was checked:</strong> an evaluation script runs 15 buyer scenarios on the synthetic data. It confirms with an independent checker that no result breaks a strict
        requirement, compares the ranking with cheapest-first and newest-first baselines, and measures how stable the ranking is when weights change slightly.
        The results are in <code>ml/reports/recommender_evaluation.md</code>. There is no real user feedback, so these checks show the rule behaves as designed, not that buyers would agree with it.
      </p>
      <p className="text-xs text-slate-500">{c.score_label}</p>
    </div>
  );
}
