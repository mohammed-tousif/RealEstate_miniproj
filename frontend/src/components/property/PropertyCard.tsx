"use client";

import Link from "next/link";
import type { PropertySummary } from "@/lib/types";
import { acresAndGuntas, formatArea, formatINRShort } from "@/lib/format";
import { label, useCompare, useMeta } from "@/lib/providers";
import { Badge, OriginBadge, cx } from "@/components/ui";
import { PropertyVisual } from "./PropertyVisual";

/** Declared-document share as a small coloured dot plus "3/7 docs": the full meter lives on the detail page. */
function DocsDot({ provided, applicable, score }: { provided: number; applicable: number; score: number }) {
  const color = score >= 0.75 ? "bg-emerald-500" : score >= 0.45 ? "bg-amber-500" : "bg-red-500";
  return (
    <span className="flex items-center gap-1.5" title="Documents the seller declared as provided (not verified)">
      <span className={cx("h-2 w-2 rounded-full", color)} aria-hidden="true" />
      {provided} of {applicable} docs declared
    </span>
  );
}

export function PropertyCard({ p, extra }: { p: PropertySummary; extra?: React.ReactNode }) {
  const meta = useMeta();
  const compare = useCompare();
  const inCompare = compare.has(p.id);
  const farmland = p.property_type === "agricultural_land";
  const road = label(meta, "RoadAccess", p.road_access);
  return (
    <article className="group flex flex-col overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-lg">
      <Link href={`/properties/${p.id}`} className="relative block aspect-[16/9] overflow-hidden">
        <PropertyVisual type={p.property_type} image={p.cover_image_url} />
        <div className="absolute inset-x-3 top-3 flex flex-wrap items-start justify-between gap-1">
          <span className="rounded-full bg-white/95 px-2.5 py-1 text-xs font-medium text-ink-800 shadow-sm">{label(meta, "PropertyType", p.property_type)}</span>
          {p.listing_status !== "approved" && <Badge tone="amber" className="bg-white/95">{label(meta, "ListingStatus", p.listing_status)}</Badge>}
        </div>
        {(p.is_synthetic || p.source_url) && (
          <div className="absolute bottom-3 left-3 [&>span]:bg-white/95 [&>span]:shadow-sm">
            <OriginBadge p={p} />
          </div>
        )}
      </Link>
      <div className="flex flex-1 flex-col p-5">
        <p className="text-lg font-semibold text-ink-900">{formatINRShort(p.asking_price_inr)}</p>
        <Link href={`/properties/${p.id}`} className="mt-1 line-clamp-1 text-[15px] font-medium text-ink-800 hover:text-brand-700" title={p.title}>
          {p.title}
        </Link>
        <p className="mt-1 flex items-center gap-1 text-sm text-ink-500">
          <svg viewBox="0 0 20 20" className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M10 18s6-5.2 6-10a6 6 0 1 0-12 0c0 4.8 6 10 6 10Z" /><circle cx="10" cy="8" r="2" /></svg>
          {p.locality.locality_name}, {p.locality.city}
        </p>
        <p className="mt-3 text-sm text-ink-700">
          {farmland ? acresAndGuntas(p.normalized_area_sqft) : formatArea(p.area_value, p.area_unit)}
          <span className="mx-1.5 text-slate-300">·</span>
          <span className={p.road_access === "unknown" ? "text-amber-700" : undefined}>{p.road_access === "unknown" ? "Road access unknown" : road}</span>
        </p>
        {extra}
        <div className="mt-auto pt-4">
          <div className="flex items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs text-ink-500">
            <DocsDot provided={p.documents_provided} applicable={p.documents_applicable} score={p.documentation_completeness} />
            <label className={cx("flex cursor-pointer items-center gap-1.5 rounded-full px-2 py-1 transition", inCompare ? "bg-brand-50 text-brand-800" : "hover:bg-slate-100")}>
              <input type="checkbox" checked={inCompare} onChange={() => compare.toggle(p.id)} className="h-3.5 w-3.5 rounded border-slate-300 text-brand-700 focus:ring-brand-500" />
              Compare
            </label>
          </div>
        </div>
      </div>
    </article>
  );
}

export function PropertyCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white">
      <div className="aspect-[16/9] animate-pulse bg-slate-200" />
      <div className="space-y-3 p-5">
        <div className="h-5 w-24 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
      </div>
    </div>
  );
}
