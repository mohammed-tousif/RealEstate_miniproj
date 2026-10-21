"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { PropertySummary } from "@/lib/types";
import { EmptyState, ErrorState, LinkButton, PageHeader, Skeleton } from "@/components/ui";
import { PropertyCard } from "@/components/property/PropertyCard";
import { RequireRole } from "@/components/RequireRole";

function Favourites() {
  const [items, setItems] = useState<PropertySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.favorites().then(setItems).catch((e: ApiError) => setError(e.message));
  }, []);
  return (
    <div className="mx-auto max-w-7xl px-4 py-10 md:py-14">
      <PageHeader title="Saved properties" />
      {error ? <ErrorState message={error} /> : items === null ? <Skeleton className="h-64 w-full" /> : items.length === 0 ? (
        <EmptyState title="No saved properties" action={<LinkButton href="/properties">Explore listings</LinkButton>}>Use &ldquo;Save to favourites&rdquo; on a listing page.</EmptyState>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{items.map((p) => <PropertyCard key={p.id} p={p} />)}</div>
      )}
    </div>
  );
}

export default function FavouritesPage() {
  return <RequireRole roles={["buyer", "seller", "admin"]}><Favourites /></RequireRole>;
}
