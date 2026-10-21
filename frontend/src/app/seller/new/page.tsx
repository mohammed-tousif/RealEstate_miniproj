"use client";

import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { RequireRole } from "@/components/RequireRole";
import { ListingForm } from "@/components/seller/ListingForm";

export default function NewListingPage() {
  const router = useRouter();
  return (
    <RequireRole roles={["seller", "admin"]}>
      <div className="mx-auto max-w-3xl px-4 py-10 md:py-14">
        <PageHeader title="Add a listing" subtitle="You can add photos after the listing is saved." />
        <ListingForm onSaved={(p) => router.push(`/seller/${p.id}/edit?created=1`)} />
      </div>
    </RequireRole>
  );
}
