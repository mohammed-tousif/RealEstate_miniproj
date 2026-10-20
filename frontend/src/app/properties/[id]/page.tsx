"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, mediaUrl } from "@/lib/api";
import { acresAndGuntas, formatArea, formatDate, formatINR, formatINRShort, formatSqft } from "@/lib/format";
import { label, useAuth, useCompare, useMeta } from "@/lib/providers";
import type { DocumentInfo, PropertyDetail, SimilarResponse } from "@/lib/types";
import { Alert, Badge, Button, Card, EmptyState, ErrorState, LinkButton, Skeleton, SyntheticBadge, Textarea, cx } from "@/components/ui";
import { DocMeter } from "@/components/property/DocMeter";
import { MapView } from "@/components/property/MapView";
import { PropertyCard } from "@/components/property/PropertyCard";
import { PropertyVisual } from "@/components/property/PropertyVisual";
import { PriceCard } from "@/components/price/PriceCard";

const DOC_TONE: Record<string, "green" | "amber" | "red" | "slate" | "blue"> = {
  verified: "green",
  verification_pending: "blue",
  provided_unverified: "amber",
  not_provided: "red",
  unknown: "slate",
  not_applicable: "slate",
};

function Fact({ k, v, warn }: { k: string; v: React.ReactNode; warn?: boolean }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2 text-sm last:border-0">
      <dt className="text-slate-500">{k}</dt>
      <dd className={cx("text-right font-medium", warn ? "text-amber-700" : "text-slate-800")}>{v}</dd>
    </div>
  );
}

function DocumentChecklist({ docs }: { docs: DocumentInfo[] }) {
  const applicable = docs.filter((d) => d.applicable);
  const other = docs.filter((d) => !d.applicable);
  return (
    <div>
      <ul className="divide-y divide-slate-100">
        {[...applicable, ...other].map((d) => (
          <li key={d.document_type} className="py-3">
            <details>
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                <span className="text-sm font-medium text-slate-800">{d.label}</span>
                <Badge tone={DOC_TONE[d.display_status]}>{d.display_label}</Badge>
              </summary>
              <p className="mt-2 text-sm text-slate-600">{d.guidance}</p>
              {d.applicable_authority && <p className="mt-1 text-xs text-slate-500">Authority: {d.applicable_authority}</p>}
            </details>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-slate-500">
        &ldquo;Provided&rdquo; means the seller says they have the document. PropWise has not verified any document, and
        a provided document does not by itself establish clear title. Check records with the issuing authority
        (for example the Karnataka Bhoomi land-records service for RTC) and consult a qualified lawyer before buying.
      </p>
    </div>
  );
}

function AdminReview({ p, onDone }: { p: PropertyDetail; onDone: (d: PropertyDetail) => void }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const act = async (action: "approve" | "reject" | "flag") => {
    setBusy(action);
    setError(null);
    try {
      onDone(await api.adminReview(p.id, action, reason || undefined));
      setReason("");
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Card className="border-amber-300 p-4">
      <p className="text-sm font-semibold text-slate-900">Admin review · status: {p.listing_status}</p>
      {p.review_reason && <p className="mt-1 text-sm text-slate-600">Last reason: {p.review_reason}</p>}
      <Textarea className="mt-3" rows={2} placeholder="Reason (required to reject or flag)" value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Review reason" />
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => act("approve")} loading={busy === "approve"}>Approve</Button>
        <Button size="sm" variant="danger" onClick={() => act("reject")} loading={busy === "reject"}>Reject</Button>
        <Button size="sm" variant="secondary" onClick={() => act("flag")} loading={busy === "flag"}>Flag</Button>
      </div>
    </Card>
  );
}

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const meta = useMeta();
  const { user } = useAuth();
  const compare = useCompare();
  const [p, setP] = useState<PropertyDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [img, setImg] = useState(0);
  const [fav, setFav] = useState<boolean | null>(null);
  const [similar, setSimilar] = useState<SimilarResponse["items"]>([]);

  const load = useCallback(() => {
    setError(null);
    api.getProperty(id).then(setP).catch(setError);
  }, [id]);
  useEffect(load, [load, user]);

  useEffect(() => {
    if (!p) return;
    api.similar(p.id).then((r) => setSimilar(r.items.slice(0, 3))).catch(() => setSimilar([]));
  }, [p]);

  useEffect(() => {
    if (!user || !p) return setFav(null);
    api.favorites().then((f) => setFav(f.some((x) => x.id === p.id))).catch(() => setFav(null));
  }, [user, p]);

  if (error)
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        {error.status === 404 ? (
          <EmptyState title="Listing not found" action={<LinkButton href="/properties" variant="secondary">Back to listings</LinkButton>}>
            It may have been archived, or it is awaiting review and only visible to its owner.
          </EmptyState>
        ) : (
          <ErrorState message={error.message} onRetry={load} />
        )}
      </div>
    );

  if (!p)
    return (
      <div className="mx-auto max-w-7xl space-y-4 px-4 py-8">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="aspect-[16/7] w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );

  const farmland = p.property_type === "agricultural_land";
  const toggleFav = async () => {
    if (fav) await api.removeFavorite(p.id);
    else await api.addFavorite(p.id);
    setFav(!fav);
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <nav className="mb-4 text-sm text-slate-500"><Link href="/properties" className="hover:text-brand-700">Explore</Link> / {p.locality.city} / {p.locality.locality_name}</nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="brand">{label(meta, "PropertyType", p.property_type)}</Badge>
            {p.is_synthetic && <SyntheticBadge />}
            {p.listing_status !== "approved" && <Badge tone="amber">{label(meta, "ListingStatus", p.listing_status)}</Badge>}
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 md:text-3xl">{p.title}</h1>
          <p className="mt-1 text-slate-600">{p.general_address ?? `${p.locality.locality_name}, ${p.locality.city}`}</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-semibold text-slate-900">{formatINRShort(p.asking_price_inr)}</p>
          <p className="text-sm text-slate-500">{formatINR(p.asking_price_inr)} asking price</p>
          <p className="text-sm text-slate-500">≈ {formatINR(p.price_per_sqft_inr)} per sq ft</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant={compare.has(p.id) ? "primary" : "secondary"} size="sm" onClick={() => compare.toggle(p.id)}>
          {compare.has(p.id) ? "Added to compare" : "Add to compare"}
        </Button>
        {user && fav !== null && (
          <Button variant="secondary" size="sm" onClick={toggleFav} aria-pressed={fav}>{fav ? "★ Saved" : "☆ Save to favourites"}</Button>
        )}
        {(p.is_owner || user?.role === "admin") && <LinkButton href={`/seller/${p.id}/edit`} variant="secondary" className="px-3 py-1.5">Edit listing</LinkButton>}
      </div>

      {p.is_synthetic && (
        <div className="mt-4"><Alert tone="blue">This is a synthetic demonstration listing. It is not a real property for sale and its price is not market data.</Alert></div>
      )}

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_380px]">
        <div className="space-y-8">
          <section aria-label="Photos">
            <div className="aspect-[16/9] overflow-hidden rounded-xl border border-slate-200">
              <PropertyVisual type={p.property_type} image={p.images[img]?.url} />
            </div>
            {p.images.length > 1 && (
              <div className="mt-2 flex gap-2 overflow-x-auto">
                {p.images.map((im, i) => (
                  <button key={im.id} onClick={() => setImg(i)} className={cx("h-16 w-24 shrink-0 overflow-hidden rounded-md border-2", i === img ? "border-brand-600" : "border-transparent")} aria-label={`Photo ${i + 1}`}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={mediaUrl(im.url) ?? ""} alt="" className="h-full w-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold">About this property</h2>
            <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{p.description || "No description provided."}</p>
          </section>

          {p.risk_flags.length > 0 && (
            <Alert tone={p.risk_flags.some((f) => f.severity === "high") ? "red" : "amber"} title="Risk flags (screening rules, not findings)">
              <ul className="space-y-1.5" data-testid="risk-flags">
                {p.risk_flags.map((f) => (
                  <li key={f.code} className="flex gap-2">
                    <Badge tone={f.severity === "high" ? "red" : f.severity === "medium" ? "amber" : "slate"} className="shrink-0 uppercase">{f.severity}</Badge>
                    <span>{f.message}</span>
                  </li>
                ))}
              </ul>
            </Alert>
          )}

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-brand-700">
            <Link href={`/chat?ask=${encodeURIComponent(`What should I check before buying listing ${p.id}?`)}`} className="font-medium underline">
              Ask the assistant about this listing
            </Link>
            <Link href={`/chat?ask=${encodeURIComponent(`Does listing ${p.id} have verified land documentation?`)}`} className="font-medium underline">
              Ask whether its documents are verified
            </Link>
          </div>

          {p.data_warnings.length > 0 && (
            <Alert title="Points to check">
              <ul className="list-disc space-y-1 pl-5">{p.data_warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </Alert>
          )}

          <section>
            <h2 className="text-lg font-semibold">Land and legal information</h2>
            <p className="mt-1 text-sm text-slate-500">As declared by the seller. These are claims, not verified facts.</p>
            <Card className="mt-3 p-4">
              <dl>
                <Fact k="Land classification" v={label(meta, "LandClassification", p.land_classification)} warn={p.land_classification === "unknown"} />
                <Fact k="Conversion (non-agricultural use)" v={label(meta, "ConversionStatus", p.conversion_status)} warn={["unknown", "not_converted"].includes(p.conversion_status)} />
                <Fact k="Layout approval" v={label(meta, "LayoutApprovalStatus", p.layout_approval_status)} warn={["unknown", "unapproved_layout"].includes(p.layout_approval_status)} />
                <Fact k="Intended use" v={label(meta, "IntendedLandUse", p.intended_land_use)} />
                {p.relevant_authorities && <Fact k="Relevant authorities" v={p.relevant_authorities} />}
                {p.restriction_notes && <Fact k="Restrictions / notes" v={p.restriction_notes} />}
              </dl>
            </Card>
          </section>

          <section>
            <div className="flex items-end justify-between">
              <h2 className="text-lg font-semibold">Documents</h2>
            </div>
            <Card className="mt-3 p-4">
              <DocMeter provided={p.documents_provided} applicable={p.documents_applicable} score={p.documentation_completeness} />
              <div className="mt-3"><DocumentChecklist docs={p.documents} /></div>
            </Card>
          </section>

          <section>
            <h2 className="text-lg font-semibold">Location</h2>
            {p.latitude && p.longitude ? (
              <div className="mt-3"><MapView items={[p]} height={320} single /></div>
            ) : (
              <p className="mt-3 rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">The seller has not provided a map location.</p>
            )}
            <p className="mt-2 text-xs text-slate-500">
              {!p.latitude ? `Locality: ${p.locality.locality_name}, ${p.locality.city}.` : p.coordinates_approximate ? "Approximate location for demonstration; not a surveyed boundary." : "Location provided by the seller."}
              {p.distance_to_city_centre_km !== null && ` About ${p.distance_to_city_centre_km} km straight-line from ${p.locality.city} centre.`}
            </p>
          </section>

          {similar.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold">Similar listings</h2>
              <p className="mt-1 text-sm text-slate-500">Nearest approved listings by type, price, area, location, road access and documents (k-nearest neighbours on standardised features).</p>
              <div className="mt-3 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {similar.map((s) => (
                  <div key={s.property.id} className="space-y-2">
                    <PropertyCard p={s.property} />
                    {s.similarities.length > 0 && <p className="text-xs text-slate-500">Similar: {s.similarities.join(", ")}.</p>}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          {user?.role === "admin" && <AdminReview p={p} onDone={setP} />}
          {p.is_owner && p.review_reason && p.listing_status !== "approved" && (
            <Alert tone="red" title={`Listing ${p.listing_status}`}>{p.review_reason}</Alert>
          )}
          <Card className="p-4">
            <h2 className="text-sm font-semibold text-slate-900">Key facts</h2>
            <dl className="mt-2">
              <Fact k="Area" v={formatArea(p.area_value, p.area_unit)} />
              <Fact k="In sq ft" v={formatSqft(p.normalized_area_sqft)} />
              {farmland && <Fact k="In acres / guntas" v={acresAndGuntas(p.normalized_area_sqft)} />}
              {p.plot_width_ft && p.plot_length_ft && <Fact k="Dimensions" v={`${Number(p.plot_width_ft)} × ${Number(p.plot_length_ft)} ft`} />}
              <Fact k="Road access" v={label(meta, "RoadAccess", p.road_access)} warn={p.road_access === "unknown"} />
              {p.road_frontage_ft && <Fact k="Road frontage" v={`${Number(p.road_frontage_ft)} ft`} />}
              {p.is_corner_plot !== null && <Fact k="Corner plot" v={p.is_corner_plot ? "Yes" : "No"} />}
              <Fact k="Locality" v={`${p.locality.locality_name}, ${p.locality.city}`} />
              <Fact k="Listed on" v={formatDate(p.created_at)} />
              <Fact k="Data source" v={p.is_synthetic ? "Synthetic generator" : p.data_source.replace(/_/g, " ")} />
            </dl>
          </Card>
          <Card className="p-4">
            <h2 className="text-sm font-semibold text-slate-900">Nearby amenities</h2>
            {p.amenities.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No amenities listed.</p>
            ) : (
              <ul className="mt-2 space-y-1.5 text-sm">
                {p.amenities.map((a) => (
                  <li key={a.code} className="flex justify-between">
                    <span>{a.label}</span>
                    {a.approx_distance_km && <span className="text-slate-500">~{Number(a.approx_distance_km)} km{a.distance_is_synthetic ? "*" : ""}</span>}
                  </li>
                ))}
              </ul>
            )}
            {p.amenities.some((a) => a.distance_is_synthetic) && <p className="mt-2 text-xs text-slate-500">* Synthetic demo distances.</p>}
          </Card>
          <PriceCard propertyId={p.id} />
        </aside>
      </div>
    </div>
  );
}
