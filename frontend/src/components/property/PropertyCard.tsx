"use client";

import Link from "next/link";
import type { PropertySummary } from "@/lib/types";
import { acresAndGuntas, formatArea, formatINRShort, formatSqft } from "@/lib/format";
import { label, useCompare, useMeta } from "@/lib/providers";
import { Badge, OriginBadge, cx } from "@/components/ui";
import { DocMeter } from "./DocMeter";
import { PropertyVisual } from "./PropertyVisual";

export function PropertyCard({ p, extra }: { p: PropertySummary; extra?: React.ReactNode }) {
  const meta = useMeta();
  const compare = useCompare();
  const inCompare = compare.has(p.id);
  const farmland = p.property_type === "agricultural_land";
  return (
    <article className="group flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card transition hover:shadow-md">
      <Link href={`/properties/${p.id}`} className="relative block aspect-[16/10] overflow-hidden">
        <PropertyVisual type={p.property_type} image={p.cover_image_url} />
        <div className="absolute left-2 top-2 flex flex-wrap gap-1">
          <Badge tone="brand" className="bg-white/90">{label(meta, "PropertyType", p.property_type)}</Badge>
          {p.listing_status !== "approved" && <Badge tone="amber" className="bg-white/90">{label(meta, "ListingStatus", p.listing_status)}</Badge>}
        </div>
      </Link>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <p className="text-lg font-semibold text-slate-900">{formatINRShort(p.asking_price_inr)}</p>
          <Link href={`/properties/${p.id}`} className="mt-0.5 line-clamp-2 text-sm font-medium text-slate-800 hover:text-brand-700">
            {p.title}
          </Link>
          <p className="mt-1 text-sm text-slate-500">{p.locality.locality_name}, {p.locality.city}</p>
        </div>
        <dl className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <dt className="text-slate-500">Area</dt>
            <dd className="font-medium text-slate-800">{farmland ? acresAndGuntas(p.normalized_area_sqft) : formatArea(p.area_value, p.area_unit)}</dd>
            {p.area_unit !== "sqft" && <dd className="text-slate-500">{formatSqft(p.normalized_area_sqft)}</dd>}
          </div>
          <div>
            <dt className="text-slate-500">Road access</dt>
            <dd className={cx("font-medium", p.road_access === "unknown" ? "text-amber-700" : "text-slate-800")}>{label(meta, "RoadAccess", p.road_access)}</dd>
          </div>
        </dl>
        <DocMeter provided={p.documents_provided} applicable={p.documents_applicable} score={p.documentation_completeness} compact />
        {extra}
        <div className="mt-auto flex items-center justify-between gap-2 pt-1">
          {p.is_synthetic || p.source_url ? <OriginBadge p={p} /> : <span />}
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-600">
            <input type="checkbox" checked={inCompare} onChange={() => compare.toggle(p.id)} className="h-3.5 w-3.5 rounded border-slate-300 text-brand-700 focus:ring-brand-500" />
            Compare
          </label>
        </div>
      </div>
    </article>
  );
}

export function PropertyCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="aspect-[16/10] animate-pulse bg-slate-200" />
      <div className="space-y-2 p-4">
        <div className="h-5 w-24 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
      </div>
    </div>
  );
}
