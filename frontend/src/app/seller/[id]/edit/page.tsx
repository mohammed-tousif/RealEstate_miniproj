"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { PropertyDetail } from "@/lib/types";
import { Alert, ErrorState, PageHeader, Skeleton } from "@/components/ui";
import { RequireRole } from "@/components/RequireRole";
import { ListingForm } from "@/components/seller/ListingForm";
import { PhotoManager } from "@/components/seller/PhotoManager";

function EditInner() {
  const { id } = useParams<{ id: string }>();
  const created = useSearchParams().get("created") === "1";
  const [p, setP] = useState<PropertyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [formKey, setFormKey] = useState(0);

  const load = useCallback(() => {
    api.getProperty(id).then(setP).catch((e: ApiError) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  if (error) return <div className="mx-auto max-w-3xl px-4 py-10 md:py-14"><ErrorState message={error} onRetry={load} /></div>;
  if (!p) return <div className="mx-auto max-w-3xl px-4 py-10 md:py-14"><Skeleton className="h-96 w-full" /></div>;

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-10 md:py-14">
      <PageHeader title="Edit listing" subtitle={<>Status: <strong>{p.listing_status}</strong> · <Link className="text-brand-700 underline" href={`/properties/${p.id}`}>View listing</Link></>} />
      {created && <Alert tone="green" title="Listing submitted">It is pending admin review. Add photos below while you wait.</Alert>}
      {p.review_reason && p.listing_status !== "approved" && <Alert tone="red" title={`Reviewer note (${p.listing_status})`}>{p.review_reason}</Alert>}
      <PhotoManager p={p} onChange={load} />
      {saved && <Alert tone="green">Changes saved. The listing is back in the review queue.</Alert>}
      <ListingForm key={formKey} existing={p} onSaved={(d) => { setP(d); setSaved(true); setFormKey((k) => k + 1); window.scrollTo({ top: 0, behavior: "smooth" }); }} />
    </div>
  );
}

export default function EditListingPage() {
  return <RequireRole roles={["seller", "admin"]}><Suspense fallback={null}><EditInner /></Suspense></RequireRole>;
}
