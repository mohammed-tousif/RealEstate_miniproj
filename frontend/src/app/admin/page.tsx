"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatINRShort, percent } from "@/lib/format";
import { label, useMeta } from "@/lib/providers";
import type { AdminStats, PropertyList } from "@/lib/types";
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Pagination, Skeleton, cx } from "@/components/ui";
import { RequireRole } from "@/components/RequireRole";
import { StatsCharts } from "@/components/admin/StatsCharts";

const TABS = ["pending", "flagged", "rejected", "approved"] as const;

function Admin() {
  const meta = useMeta();
  const [tab, setTab] = useState<(typeof TABS)[number]>("pending");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PropertyList | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api.adminQueue(tab, page).then(setData).catch((e: ApiError) => setError(e.message));
    api.adminStats().then(setStats).catch(() => setStats(null));
  }, [tab, page]);
  useEffect(load, [load]);

  const act = async (id: string, action: "approve" | "reject" | "flag") => {
    let reason: string | undefined;
    if (action !== "approve") {
      const r = window.prompt(`Reason to ${action} this listing (shown to the seller):`);
      if (!r?.trim()) return;
      reason = r.trim();
    }
    setBusy(id + action);
    try {
      await api.adminReview(id, action, reason);
      load();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <PageHeader title="Admin dashboard" subtitle="Review submitted listings. Approved listings become publicly searchable." />

      {stats ? (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            {[
              ["Total listings", stats.total_listings],
              ["Awaiting review", stats.listings_by_status.pending ?? 0],
              ["Synthetic", stats.listings_by_origin.synthetic ?? 0],
              ["Genuine", stats.listings_by_origin.genuine ?? 0],
            ].map(([k, v]) => (
              <Card key={k} className="p-4"><p className="text-sm text-slate-500">{k}</p><p className="mt-1 text-2xl font-semibold">{v}</p></Card>
            ))}
          </div>
          <StatsCharts stats={stats} typeLabels={meta?.enums.PropertyType} />
        </>
      ) : (
        <Skeleton className="h-40 w-full" />
      )}

      <section>
        <div className="mb-4 flex gap-1 border-b border-slate-200" role="tablist">
          {TABS.map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => { setTab(t); setPage(1); }} className={cx("-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize", tab === t ? "border-brand-700 text-brand-800" : "border-transparent text-slate-600 hover:text-slate-900")}>
              {t}{stats?.listings_by_status[t] ? ` (${stats.listings_by_status[t]})` : ""}
            </button>
          ))}
        </div>
        {error && <ErrorState message={error} onRetry={load} />}
        {!data ? <Skeleton className="h-64 w-full" /> : data.items.length === 0 ? (
          <EmptyState title={`No ${tab} listings`} />
        ) : (
          <>
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="w-full min-w-[860px] text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                  <tr><th className="p-3">Listing</th><th className="p-3">Type</th><th className="p-3">Price</th><th className="p-3">Documents declared</th><th className="p-3">Submitted</th><th className="p-3 text-right">Actions</th></tr>
                </thead>
                <tbody>
                  {data.items.map((p) => (
                    <tr key={p.id} className="border-b border-slate-100 last:border-0">
                      <td className="p-3">
                        <Link href={`/properties/${p.id}`} className="font-medium text-slate-900 hover:text-brand-700">{p.title}</Link>
                        <div className="text-xs text-slate-500">{p.locality.locality_name}, {p.locality.city} {p.is_synthetic && <Badge tone="violet" className="ml-1">synthetic</Badge>}</div>
                      </td>
                      <td className="p-3">{label(meta, "PropertyType", p.property_type)}</td>
                      <td className="p-3">{formatINRShort(p.asking_price_inr)}</td>
                      <td className="p-3"><span className={p.documentation_completeness < 0.45 ? "text-red-700" : ""}>{p.documents_provided}/{p.documents_applicable} ({percent(p.documentation_completeness)})</span></td>
                      <td className="p-3 text-slate-500">{formatDate(p.created_at)}</td>
                      <td className="p-3">
                        <div className="flex justify-end gap-1.5">
                          {tab !== "approved" && <Button size="sm" onClick={() => act(p.id, "approve")} loading={busy === p.id + "approve"}>Approve</Button>}
                          {tab !== "rejected" && <Button size="sm" variant="danger" onClick={() => act(p.id, "reject")} loading={busy === p.id + "reject"}>Reject</Button>}
                          {tab !== "flagged" && <Button size="sm" variant="secondary" onClick={() => act(p.id, "flag")} loading={busy === p.id + "flag"}>Flag</Button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-6"><Pagination page={data.page} totalPages={data.total_pages} onPage={setPage} /></div>
          </>
        )}
      </section>
    </div>
  );
}

export default function AdminPage() {
  return <RequireRole roles={["admin"]}><Admin /></RequireRole>;
}
