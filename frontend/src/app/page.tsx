"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, toQueryString } from "@/lib/api";
import { parseINR } from "@/lib/format";
import { useMeta } from "@/lib/providers";
import type { PropertySummary } from "@/lib/types";
import { Alert, Button, Input, Select } from "@/components/ui";
import { PropertyCard, PropertyCardSkeleton } from "@/components/property/PropertyCard";

const CATEGORIES = [
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
      <section className="border-b border-slate-200 bg-gradient-to-b from-brand-50 to-white">
        <div className="mx-auto max-w-7xl px-4 py-14 md:py-20">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">Hubballi · Dharwad</p>
          <h1 className="mt-2 max-w-3xl text-4xl font-semibold tracking-tight text-slate-900 md:text-5xl">
            Property research that explains itself.
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-slate-600">
            Find plots, farmland and commercial property, see how well each one fits your budget and purpose, and know
            which documents still need checking.
          </p>
          <form onSubmit={search} className="mt-8 grid max-w-4xl gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-card md:grid-cols-[1fr_1fr_1fr_auto]">
            <Select aria-label="City" value={q.city} onChange={(e) => setQ({ ...q, city: e.target.value })}>
              <option value="">Hubballi and Dharwad</option>
              <option value="Hubballi">Hubballi</option>
              <option value="Dharwad">Dharwad</option>
            </Select>
            <Select aria-label="Property type" value={q.type} onChange={(e) => setQ({ ...q, type: e.target.value })}>
              <option value="">Any property type</option>
              {Object.entries(meta?.enums.PropertyType ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Select>
            <Input aria-label="Maximum budget" placeholder="Max budget, e.g. 25 lakh" value={q.budget} onChange={(e) => { setErr(null); setQ({ ...q, budget: e.target.value }); }} />
            <Button type="submit" className="px-6">Search</Button>
          </form>
          {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
          <p className="mt-4 text-sm text-slate-500">
            AI recommendations, price estimates and the assistant arrive in the next milestones.{" "}
            <Link href="/about" className="text-brand-700 underline">How it works</Link>
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12">
        <h2 className="text-xl font-semibold">Browse by category</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {CATEGORIES.map((c) => (
            <Link key={c.type} href={`/properties?property_type=${c.type}`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-card transition hover:border-brand-300 hover:shadow-md">
              <p className="font-medium text-slate-900">{meta?.enums.PropertyType?.[c.type] ?? c.type}</p>
              <p className="mt-1 text-sm text-slate-500">{c.blurb}</p>
              <p className="mt-3 text-xs font-medium text-brand-700">{counts[c.type] !== undefined ? `${counts[c.type]} listings` : " "}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-12">
        <div className="flex items-end justify-between">
          <h2 className="text-xl font-semibold">Latest listings</h2>
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
          <h2 className="text-xl font-semibold">How PropWise works</h2>
          <ol className="mt-6 grid gap-6 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="rounded-xl border border-slate-200 p-5">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-700 text-sm font-semibold text-white">{i + 1}</span>
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
