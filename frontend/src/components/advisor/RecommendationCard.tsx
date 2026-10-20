"use client";

import Link from "next/link";
import { formatArea, formatINRShort, formatSqft } from "@/lib/format";
import { label, useCompare, useMeta } from "@/lib/providers";
import type { Recommendation } from "@/lib/types";
import { Badge, Button, Card, SyntheticBadge } from "@/components/ui";
import { Explanations, FactorBars, ScoreBadge } from "./MatchDetails";

export function RecommendationCard({ r }: { r: Recommendation }) {
  const meta = useMeta();
  const compare = useCompare();
  const p = r.property;
  return (
    <Card className="p-5">
      <article className="grid gap-5 md:grid-cols-[1fr_240px]" aria-label={`Recommendation ${r.rank}`}>
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="slate">#{r.rank}</Badge>
            <Badge tone="brand">{label(meta, "PropertyType", p.property_type)}</Badge>
            {p.is_synthetic && <SyntheticBadge />}
          </div>
          <div>
            <Link href={`/properties/${p.id}`} className="text-lg font-semibold text-slate-900 hover:text-brand-700">{p.title}</Link>
            <p className="text-sm text-slate-600">
              {p.locality.locality_name}, {p.locality.city} · {formatArea(p.area_value, p.area_unit)}{p.area_unit !== "sqft" && ` (${formatSqft(p.normalized_area_sqft)})`} ·{" "}
              <span className="font-semibold text-slate-900">{formatINRShort(p.asking_price_inr)}</span>
            </p>
          </div>
          <Explanations r={r} />
        </div>
        <div className="space-y-4">
          <ScoreBadge score={r.score} coverage={r.data_coverage} />
          <FactorBars r={r} />
          <Button size="sm" variant={compare.has(p.id) ? "primary" : "secondary"} onClick={() => compare.toggle(p.id)} className="w-full">
            {compare.has(p.id) ? "Added to compare" : "Add to compare"}
          </Button>
        </div>
      </article>
    </Card>
  );
}
