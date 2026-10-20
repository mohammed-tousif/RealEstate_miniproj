"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, toQueryString } from "@/lib/api";
import { parseINR } from "@/lib/format";
import { useMeta } from "@/lib/providers";
import type { PropertySummary, PropertyType } from "@/lib/types";
import { Alert, Button, Input, Select } from "@/components/ui";
import { PropertyCard, PropertyCardSkeleton } from "@/components/property/PropertyCard";
import { CategoryIcon } from "@/components/property/PropertyVisual";

const CATEGORIES: { type: PropertyType; blurb: string }[] = [
  { type: "residential_plot", blurb: "Plots for building a home" },
  { type: "agricultural_land", blurb: "Farmland and agricultural parcels" },
  { type: "commercial_plot", blurb: "Plots for shops and offices" },
  { type: "independent_house", blurb: "Built independent houses" },
  { type: "commercial_building", blurb: "Built commercial premises" },
];

const STEPS = [
  { title: "Discover", text: "Search one structured database of listings with Indian land units, land classification and declared documents." },
  { title: "Rank and estimate", text: "Get recommendations ranked by a transparent suitability score, and an indicative price from a trained regression model." },
  { title: "Verify", text: "See exactly which documents are missing or unverified, and what to check independently before you buy." },
];

export default function Home() {
  const router = useRouter();
  const meta = useMeta();
  const [featured, setFeatured] = useState<PropertySummary[] | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [q, setQ] = useState({ city: "", type: "", budget: "" });
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.searchProperties({ sort: "newest", page_size: 6 }).then((r) => setFeatured(r.items)).catch(() => setFeatured([]));
    Promise.all(CATEGORIES.map((c) => api.searchProperties({ property_type: [c.type], page_size: 1 }).then((r) => [c.type, r.total] as const)))
      .then((pairs) => setCounts(Object.fromEntries(pairs)))
      .catch(() => setCounts({}));
  }, []);

  const search = (e: React.FormEvent) => {
    e.preventDefault();
    const max = q.budget ? parseINR(q.budget) : null;
    if (q.budget && max === null) return setErr("Budget not understood. Try 25 lakh or 1.2 crore.");
    router.push(`/properties${toQueryString({ city: q.city, property_type: q.type ? [q.type] : undefined, max_price: max ?? undefined })}`);
  };

  return (
    <>
      <section className="relative isolate overflow-hidden bg-sky-hero">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/theme/hero-building.jpg" alt="" aria-hidden="true" className="absolute inset-x-0 bottom-0 -z-10 h-full w-full object-cover object-bottom" />
        <div className="absolute inset-x-0 top-0 -z-10 h-2/3 bg-sky-fade" aria-hidden="true" />
        <div className="mx-auto flex min-h-[640px] max-w-7xl flex-col items-center px-4 pb-48 pt-32 text-center text-white md:min-h-[760px] md:pb-64 md:pt-40">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-white/90">Hubballi · Dharwad</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-tight tracking-tight drop-shadow-[0_2px_12px_rgba(29,63,99,.35)] md:text-[56px] md:leading-[1.15]">
            Property research that explains itself.
          </h1>
          <p className="mt-5 max-w-3xl text-lg font-semibold leading-relaxed drop-shadow-[0_1px_8px_rgba(29,63,99,.35)]">
            Find plots, farmland and commercial property, see how well each one fits your budget and purpose, and know
            which documents still need checking.
          </p>
          <div className="mt-10 w-full max-w-5xl text-left">
            <div className="flex gap-1" role="navigation" aria-label="Ways to search">
              <span className="rounded-t-md bg-white px-6 py-2 text-[15px] font-medium text-ink-900">Search listings</span>
              <Link href="/advisor" className="rounded-t-md bg-white/70 px-6 py-2 text-[15px] font-medium text-ink-700 transition hover:bg-white">Advisor</Link>
              <Link href="/estimate" className="hidden rounded-t-md bg-white/70 px-6 py-2 text-[15px] font-medium text-ink-700 transition hover:bg-white sm:block">Price estimate</Link>
            </div>
            <form onSubmit={search} className="grid gap-2 rounded-b-design rounded-tr-design bg-white p-3 shadow-float md:grid-cols-[1fr_1.2fr_1.2fr_auto] md:items-center md:gap-0 md:divide-x md:divide-slate-200 md:py-3">
              <Select aria-label="City" value={q.city} onChange={(e) => setQ({ ...q, city: e.target.value })} className="!border-transparent text-[15px] text-ink-700 shadow-none md:rounded-none">
                <option value="">Hubballi and Dharwad</option>
                <option value="Hubballi">Hubballi</option>
                <option value="Dharwad">Dharwad</option>
              </Select>
              <Select aria-label="Property type" value={q.type} onChange={(e) => setQ({ ...q, type: e.target.value })} className="!border-transparent text-[15px] text-ink-700 shadow-none md:rounded-none">
                <option value="">Any property type</option>
                {Object.entries(meta?.enums.PropertyType ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </Select>
              <div className="relative">
                <svg viewBox="0 0 24 24" className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-500" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
                <Input aria-label="Maximum budget" placeholder="Max budget, e.g. 25 lakh" value={q.budget} onChange={(e) => { setErr(null); setQ({ ...q, budget: e.target.value }); }} className="!border-transparent pl-10 text-[15px] md:rounded-none" />
              </div>
              <div className="md:pl-3">
                <Button type="submit" className="w-full px-12 py-3 text-[15px] md:w-auto">Search</Button>
              </div>
            </form>
            {err && <p className="mt-2 rounded-md bg-white/90 px-3 py-1 text-sm text-red-600">{err}</p>}
          </div>
        </div>
      </section>

      <section className="relative -mt-28 rounded-tl-[60px] bg-ink-gradient text-white shadow-float md:-mt-40 md:rounded-tl-[108px]">
        <div className="mx-auto max-w-7xl px-4 pb-14 pt-10">
          <div className="flex items-end justify-between gap-4">
            <h2 className="text-[28px] font-medium">Browse by category</h2>
            <Link href="/about" className="text-sm text-ink-400 hover:text-white">How it works</Link>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-x-5 gap-y-7 sm:grid-cols-3 lg:grid-cols-5">
            {CATEGORIES.map((c) => (
              <Link key={c.type} href={`/properties?property_type=${c.type}`} className="group">
                <div className="flex aspect-[186/190] items-center justify-center rounded-design bg-gradient-to-br from-brand-400/90 to-brand-800 text-white ring-1 ring-white/10 transition group-hover:from-brand-300 group-hover:ring-white/40">
                  <CategoryIcon type={c.type} className="h-16 w-16 md:h-20 md:w-20" />
                </div>
                <p className="mt-4 text-base font-medium text-white">{meta?.enums.PropertyType?.[c.type] ?? c.type}</p>
                <p className="mt-1 text-sm text-ink-400">{c.blurb}</p>
                <p className="mt-1 text-sm font-medium text-brand-200">{counts[c.type] !== undefined ? `${counts[c.type]} listings` : "\u00a0"}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14">
        <div className="flex items-end justify-between">
          <h2 className="text-[28px] font-medium text-ink-900">Latest listings</h2>
          <Link href="/properties" className="text-sm font-medium text-brand-700 hover:underline">See all</Link>
        </div>
        <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {featured === null
            ? Array.from({ length: 3 }, (_, i) => <PropertyCardSkeleton key={i} />)
            : featured.map((p) => <PropertyCard key={p.id} p={p} />)}
        </div>
        {featured?.length === 0 && <p className="mt-4 text-sm text-slate-500">No listings yet. Is the backend running and seeded?</p>}
      </section>

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-12">
          <h2 className="text-[28px] font-medium text-ink-900">How PropWise works</h2>
          <ol className="mt-6 grid gap-6 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="rounded-design border border-slate-200 p-6">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-ink-gradient text-sm font-semibold text-white">{i + 1}</span>
                <p className="mt-3 font-semibold">{s.title}</p>
                <p className="mt-1 text-sm text-slate-600">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10">
        <Alert tone="blue" title="Demonstration data">
          Most listings on this site are synthetic, generated for a college project. A few, marked &ldquo;Real listing&rdquo;,
          are land listings copied from a public website with a link to the source; PropWise has not verified them and does
          not represent their sellers. Nothing here is a valuation, or legal or investment advice.
        </Alert>
      </section>
    </>
  );
}
