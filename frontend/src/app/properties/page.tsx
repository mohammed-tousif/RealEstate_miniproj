"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError, toQueryString } from "@/lib/api";
import type { PropertyList } from "@/lib/types";
import { Alert, Button, EmptyState, ErrorState, Pagination, Select, cx } from "@/components/ui";
import { FilterSidebar, type Filters } from "@/components/property/FilterSidebar";
import { MapView } from "@/components/property/MapView";
import { PropertyCard, PropertyCardSkeleton } from "@/components/property/PropertyCard";

const MULTI = ["property_type", "land_classification", "road_access", "intended_land_use", "layout_approval_status", "has_document"];
const SORTS: Record<string, string> = {
  newest: "Newest first",
  oldest: "Oldest first",
  price_asc: "Price: low to high",
  price_desc: "Price: high to low",
  area_asc: "Area: small to large",
  area_desc: "Area: large to small",
};

function readFilters(sp: URLSearchParams): Filters {
  const f: Filters = {};
  sp.forEach((v, k) => {
    if (MULTI.includes(k)) f[k] = [...((f[k] as string[]) ?? []), v];
    else f[k] = v;
  });
  return f;
}

function ListingsInner() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const filters = useMemo(() => readFilters(new URLSearchParams(sp.toString())), [sp]);
  const [data, setData] = useState<PropertyList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"list" | "map">("list");
  const [showFilters, setShowFilters] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const q = { ...filters, page_size: view === "map" ? "50" : "12" };
    api
      .searchProperties(q)
      .then(setData)
      .catch((e: ApiError) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters, view]);

  useEffect(load, [load]);

  const push = (f: Filters) => router.push(`${pathname}${toQueryString(f)}`, { scroll: false });
  const active = Object.entries(filters).filter(([k, v]) => !["sort", "page"].includes(k) && (Array.isArray(v) ? v.length : v)).length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Explore properties</h1>
          <p className="mt-1 text-sm text-slate-600">
            {data ? `${data.total.toLocaleString("en-IN")} listing${data.total === 1 ? "" : "s"} match` : "Loading listings…"}
            {active > 0 && ` · ${active} filter${active === 1 ? "" : "s"} applied`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" className="lg:hidden" onClick={() => setShowFilters(!showFilters)} aria-expanded={showFilters}>
            Filters{active ? ` (${active})` : ""}
          </Button>
          <label className="sr-only" htmlFor="sort">Sort</label>
          <Select id="sort" className="w-48" value={(filters.sort as string) ?? "newest"} onChange={(e) => push({ ...filters, sort: e.target.value, page: "1" })}>
            {Object.entries(SORTS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
          <div className="flex rounded-lg border border-slate-300 bg-white p-0.5" role="group" aria-label="View">
            {(["list", "map"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)} aria-pressed={view === v} className={cx("rounded-md px-3 py-1.5 text-sm capitalize", view === v ? "bg-brand-700 text-white" : "text-slate-700")}>
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <aside className={cx("lg:block", showFilters ? "block" : "hidden")}>
          <div className="rounded-xl border border-slate-200 bg-white p-4 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
            <FilterSidebar initial={filters} onApply={(f) => { setShowFilters(false); push(f); }} onReset={() => push({})} />
          </div>
        </aside>

        <section aria-live="polite">
          {error && <ErrorState message={error} onRetry={load} />}
          {!error && view === "map" && data && (
            <>
              <MapView items={data.items} />
              <p className="mt-2 text-xs text-slate-500">
                Showing up to 50 listings on the map. Locations are approximate.
                {data.total > 50 && " Narrow the filters to see the rest."}
              </p>
            </>
          )}
          {!error && view === "list" && (
            <>
              {loading && !data ? (
                <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }, (_, i) => <PropertyCardSkeleton key={i} />)}</div>
              ) : data && data.items.length === 0 ? (
                <EmptyState title="No listings match these filters" action={<Button variant="secondary" onClick={() => push({})}>Clear all filters</Button>}>
                  Try a higher budget, a wider area range, or another locality. We only show listings that are actually in the database.
                </EmptyState>
              ) : data ? (
                <div className={cx("grid gap-5 sm:grid-cols-2 xl:grid-cols-3", loading && "opacity-60")}>
                  {data.items.map((p) => <PropertyCard key={p.id} p={p} />)}
                </div>
              ) : null}
              {data && (
                <div className="mt-8">
                  <Pagination page={data.page} totalPages={data.total_pages} onPage={(p) => push({ ...filters, page: String(p) })} />
                </div>
              )}
            </>
          )}
          <div className="mt-6">
            <Alert tone="blue">All listings in this demo are synthetic. Prices and documents are illustrative, not market data.</Alert>
          </div>
        </section>
      </div>
    </div>
  );
}

export default function ListingsPage() {
  return (
    <Suspense fallback={null}>
      <ListingsInner />
    </Suspense>
  );
}
