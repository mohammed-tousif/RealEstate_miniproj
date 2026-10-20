"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatINRShort } from "@/lib/format";
import { label, useMeta } from "@/lib/providers";
import type { PropertyList } from "@/lib/types";
import { Badge, Button, EmptyState, ErrorState, LinkButton, PageHeader, Pagination, Skeleton } from "@/components/ui";
import { RequireRole } from "@/components/RequireRole";

const STATUS_TONE = { pending: "amber", approved: "green", rejected: "red", flagged: "red", archived: "slate" } as const;

function MyListings() {
  const meta = useMeta();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PropertyList | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.searchProperties({ mine: true, page, page_size: 20, sort: "newest" }).then(setData).catch((e: ApiError) => setError(e.message));
  }, [page]);
  useEffect(load, [load]);

  const archive = async (id: string) => {
    if (!window.confirm("Archive this listing? It will disappear from search.")) return;
    try {
      await api.archiveProperty(id);
      load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader title="My listings" subtitle="New and edited listings are reviewed by an admin before they appear in search." actions={<LinkButton href="/seller/new">Add a listing</LinkButton>} />
      {error && <ErrorState message={error} onRetry={load} />}
      {!data ? <Skeleton className="h-64 w-full" /> : data.items.length === 0 ? (
        <EmptyState title="You have no listings yet" action={<LinkButton href="/seller/new">Add your first listing</LinkButton>} />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                <tr><th className="p-3">Listing</th><th className="p-3">Type</th><th className="p-3">Price</th><th className="p-3">Status</th><th className="p-3">Listed</th><th className="p-3" /></tr>
              </thead>
              <tbody>
                {data.items.map((p) => (
                  <tr key={p.id} className="border-b border-slate-100 last:border-0">
                    <td className="p-3"><Link href={`/properties/${p.id}`} className="font-medium text-slate-900 hover:text-brand-700">{p.title}</Link><div className="text-xs text-slate-500">{p.locality.locality_name}, {p.locality.city}</div></td>
                    <td className="p-3">{label(meta, "PropertyType", p.property_type)}</td>
                    <td className="p-3">{formatINRShort(p.asking_price_inr)}</td>
                    <td className="p-3"><Badge tone={STATUS_TONE[p.listing_status]}>{label(meta, "ListingStatus", p.listing_status)}</Badge></td>
                    <td className="p-3 text-slate-500">{formatDate(p.created_at)}</td>
                    <td className="p-3 text-right">
                      <div className="flex justify-end gap-2">
                        <LinkButton href={`/seller/${p.id}/edit`} variant="secondary" className="px-3 py-1.5">Edit</LinkButton>
                        <Button variant="ghost" size="sm" onClick={() => archive(p.id)}>Archive</Button>
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
    </div>
  );
}

export default function SellerPage() {
  return <RequireRole roles={["seller", "admin"]}><MyListings /></RequireRole>;
}
