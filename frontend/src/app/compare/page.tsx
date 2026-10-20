"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { acresAndGuntas, formatArea, formatINR, formatINRShort, formatSqft, percent } from "@/lib/format";
import { label, useCompare, useMeta } from "@/lib/providers";
import { loadPreferences } from "@/lib/advisor";
import type { CompareResponse, PropertyDetail } from "@/lib/types";
import { ScoreBadge } from "@/components/advisor/MatchDetails";
import { Alert, Button, EmptyState, LinkButton, PageHeader, Skeleton, SyntheticBadge, cx } from "@/components/ui";

type Row = { label: string; get: (p: PropertyDetail) => React.ReactNode; best?: (ps: PropertyDetail[]) => string | null };

const minBy = (ps: PropertyDetail[], f: (p: PropertyDetail) => number) =>
  ps.length > 1 ? ps.reduce((a, b) => (f(b) < f(a) ? b : a)).id : null;
const maxBy = (ps: PropertyDetail[], f: (p: PropertyDetail) => number) =>
  ps.length > 1 ? ps.reduce((a, b) => (f(b) > f(a) ? b : a)).id : null;

export default function ComparePage() {
  const meta = useMeta();
  const { ids, toggle, clear } = useCompare();
  const [items, setItems] = useState<PropertyDetail[] | null>(null);
  const [missing, setMissing] = useState(0);
  const [match, setMatch] = useState<CompareResponse | null>(null);
  const [hasPrefs, setHasPrefs] = useState(false);

  useEffect(() => {
    if (ids.length === 0) return setItems([]);
    Promise.allSettled(ids.map((id) => api.getProperty(id))).then((rs) => {
      setItems(rs.flatMap((r) => (r.status === "fulfilled" ? [r.value] : [])));
      setMissing(rs.filter((r) => r.status === "rejected").length);
    });
  }, [ids]);

  useEffect(() => {
    const prefs = loadPreferences();
    setHasPrefs(!!prefs);
    const live = items?.map((p) => p.id) ?? [];
    if (!prefs || live.length < 2) return setMatch(null);
    api.compare(live, prefs).then(setMatch).catch(() => setMatch(null));
  }, [items]);
  const matchFor = (id: string) => match?.items.find((i) => i.property.id === id);

  const mixedCategories = items ? new Set(items.map((p) => (p.property_type === "agricultural_land" ? "farm" : p.property_type.startsWith("commercial") ? "commercial" : "residential"))).size > 1 : false;

  const rows: Row[] = [
    ...(match
      ? [{
          label: "Match for your preferences",
          get: (p: PropertyDetail) => {
            const m = matchFor(p.id);
            if (!m?.match) return "—";
            return (
              <div className="space-y-1">
                <div className="flex items-center gap-2"><ScoreBadge score={m.match.score} coverage={m.match.data_coverage} /><span className="text-xs text-slate-500">#{m.match.rank} of {match.items.length}</span></div>
                {m.excluded_reason && <p className="text-xs text-amber-700">Fails a strict requirement: {m.excluded_reason.toLowerCase()}</p>}
                {m.match.reasons[0] && <p className="text-xs text-slate-600">{m.match.reasons[0]}</p>}
              </div>
            );
          },
          best: () => {
            const [a, b] = [...match.items].sort((x, y) => (x.match?.rank ?? 9) - (y.match?.rank ?? 9));
            return a?.match && !a.excluded_reason && (!b?.match || a.match.score > b.match.score) ? a.property.id : null;
          },
        } as Row]
      : []),
    { label: "Asking price", get: (p) => <><span className="font-semibold">{formatINRShort(p.asking_price_inr)}</span><br /><span className="text-xs text-slate-500">{formatINR(p.asking_price_inr)}</span></>, best: (ps) => minBy(ps, (p) => Number(p.asking_price_inr)) },
    { label: "Area", get: (p) => <>{formatArea(p.area_value, p.area_unit)}<br /><span className="text-xs text-slate-500">{p.property_type === "agricultural_land" ? acresAndGuntas(p.normalized_area_sqft) : formatSqft(p.normalized_area_sqft)}</span></>, best: (ps) => maxBy(ps, (p) => Number(p.normalized_area_sqft)) },
    { label: "Price per sq ft", get: (p) => formatINR(p.price_per_sqft_inr), best: (ps) => (mixedCategories ? null : minBy(ps, (p) => Number(p.price_per_sqft_inr))) },
    { label: "Location", get: (p) => `${p.locality.locality_name}, ${p.locality.city}` },
    { label: "Property type", get: (p) => label(meta, "PropertyType", p.property_type) },
    { label: "Land classification", get: (p) => label(meta, "LandClassification", p.land_classification) },
    { label: "Conversion (claimed)", get: (p) => label(meta, "ConversionStatus", p.conversion_status) },
    { label: "Layout approval (claimed)", get: (p) => label(meta, "LayoutApprovalStatus", p.layout_approval_status) },
    { label: "Road access", get: (p) => label(meta, "RoadAccess", p.road_access) },
    { label: "Documents declared", get: (p) => `${p.documents_provided} of ${p.documents_applicable} (${percent(p.documentation_completeness)})`, best: (ps) => maxBy(ps, (p) => p.documentation_completeness) },
    { label: "Points to check", get: (p) => (p.data_warnings.length ? <ul className="list-disc pl-4 text-left text-xs">{p.data_warnings.map((w) => <li key={w}>{w}</li>)}</ul> : "None flagged") },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader
        title="Compare properties"
        subtitle="Pick up to three listings with the Compare checkbox on any card."
        actions={ids.length > 0 && <Button variant="secondary" size="sm" onClick={clear}>Clear all</Button>}
      />
      {items === null ? (
        <Skeleton className="h-96 w-full" />
      ) : items.length === 0 ? (
        <EmptyState title="Nothing to compare yet" action={<LinkButton href="/properties">Explore listings</LinkButton>}>
          Tick &ldquo;Compare&rdquo; on two or three property cards and come back here.
        </EmptyState>
      ) : (
        <>
          {missing > 0 && <div className="mb-4"><Alert>{missing} selected listing{missing > 1 ? "s are" : " is"} no longer available.</Alert></div>}
          {mixedCategories && (
            <div className="mb-4">
              <Alert title="Different kinds of property">
                Farmland, residential and commercial land are priced on different bases. Comparing their price per sq ft
                can be misleading, so no &ldquo;best&rdquo; value is highlighted for that row.
              </Alert>
            </div>
          )}
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="w-48 p-4 text-left font-medium text-slate-500">Listing</th>
                  {items.map((p) => (
                    <th key={p.id} className="p-4 text-left align-top font-normal">
                      <Link href={`/properties/${p.id}`} className="font-semibold text-slate-900 hover:text-brand-700">{p.title}</Link>
                      <div className="mt-2 flex items-center gap-2">
                        {p.is_synthetic && <SyntheticBadge />}
                        <button onClick={() => toggle(p.id)} className="text-xs text-slate-500 underline">Remove</button>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const best = r.best?.(items);
                  return (
                    <tr key={r.label} className="border-b border-slate-100 last:border-0">
                      <th scope="row" className="p-4 text-left font-medium text-slate-600">{r.label}</th>
                      {items.map((p) => (
                        <td key={p.id} className={cx("p-4 align-top", best === p.id && "bg-emerald-50")}>{r.get(p)}</td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-500">Green cells mark the lowest price, largest area, lowest price per sq ft or most documents declared, and the clearly highest match score (no highlight on a tie).{" "}
            {match
              ? `Match scores use your last Advisor preferences (engine ${match.engine_version}). ${match.score_label}`
              : hasPrefs
                ? ""
                : <>Set your preferences in the <Link href="/advisor" className="underline">Advisor</Link> to see a match score here.</>}
          </p>
          {match && items.length >= 2 && (
            <p className="mt-2 text-sm">
              <Link
                href={`/chat?ask=${encodeURIComponent(`Why does one of these rank higher: ${items.map((p) => p.id).join(", ")}?`)}`}
                className="font-medium text-brand-700 underline"
              >
                Ask the assistant why one ranks higher
              </Link>
            </p>
          )}
        </>
      )}
    </div>
  );
}
