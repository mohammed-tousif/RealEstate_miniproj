"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { applicableDocuments, defaultsForType } from "@/lib/documents";
import { formatSqft, parseINR, toSqft } from "@/lib/format";
import { useMeta } from "@/lib/providers";
import type { DocumentAvailability, ListingInput, Locality, PropertyDetail, PropertyType } from "@/lib/types";
import { Alert, Button, Card, Field, Input, Select, Textarea } from "@/components/ui";

type FormState = Omit<ListingInput, "asking_price_inr" | "locality_id"> & { price_text: string; locality_id: string };

function fromDetail(p?: PropertyDetail): FormState {
  return {
    title: p?.title ?? "",
    description: p?.description ?? "",
    property_type: p?.property_type ?? "residential_plot",
    intended_land_use: p?.intended_land_use ?? "residential",
    land_classification: p?.land_classification ?? "non_agricultural_residential",
    conversion_status: p?.conversion_status ?? "unknown",
    layout_approval_status: p?.layout_approval_status ?? "unknown",
    price_text: p ? String(Number(p.asking_price_inr)) : "",
    area_value: p ? String(Number(p.area_value)) : "",
    area_unit: p?.area_unit ?? "sqft",
    plot_width_ft: p?.plot_width_ft ? String(Number(p.plot_width_ft)) : null,
    plot_length_ft: p?.plot_length_ft ? String(Number(p.plot_length_ft)) : null,
    road_frontage_ft: p?.road_frontage_ft ? String(Number(p.road_frontage_ft)) : null,
    road_access: p?.road_access ?? "unknown",
    is_corner_plot: p?.is_corner_plot ?? null,
    locality_id: p ? String(p.locality.id) : "",
    general_address: p?.general_address ?? "",
    latitude: p?.latitude ?? null,
    longitude: p?.longitude ?? null,
    restriction_notes: p?.restriction_notes ?? "",
    additional_notes: p?.additional_notes ?? "",
    relevant_authorities: p?.relevant_authorities ?? "",
    amenities: p?.amenities.map((a) => a.code) ?? [],
  };
}

const blankToNull = (v: string | null | undefined) => (v === undefined || v === null || v.trim() === "" ? null : v.trim());

function EnumSelect({ id, group, value, onChange, exclude = [] }: { id: string; group: string; value: string; onChange: (v: string) => void; exclude?: string[] }) {
  const meta = useMeta();
  const opts = meta?.enums[group] ?? {};
  return (
    <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      {Object.entries(opts).filter(([k]) => !exclude.includes(k)).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
    </Select>
  );
}

export function ListingForm({ existing, onSaved }: { existing?: PropertyDetail; onSaved: (p: PropertyDetail) => void }) {
  const meta = useMeta();
  const [f, setF] = useState<FormState>(() => fromDetail(existing));
  const [docs, setDocs] = useState<Record<string, DocumentAvailability>>(() =>
    Object.fromEntries((existing?.documents ?? []).filter((d) => d.applicable).map((d) => [d.document_type, d.availability])),
  );
  const [consent, setConsent] = useState(!!existing);
  const [localities, setLocalities] = useState<Locality[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.localities().then(setLocalities).catch(() => setLocalities([]));
  }, []);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setF((prev) => ({ ...prev, [k]: v }));
  const changeType = (t: PropertyType) => setF((prev) => ({ ...prev, property_type: t, ...defaultsForType(t) }));
  const docList = useMemo(() => applicableDocuments(f.property_type, f.conversion_status, f.layout_approval_status), [f.property_type, f.conversion_status, f.layout_approval_status]);
  const sqft = f.area_value && !Number.isNaN(Number(f.area_value)) ? toSqft(Number(f.area_value), f.area_unit) : null;
  const isPlot = f.property_type !== "agricultural_land";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setClientError(null);
    const price = parseINR(f.price_text);
    if (!price || price <= 0) return setClientError("Enter the asking price, e.g. 1840000 or 18.4 lakh.");
    if (!f.locality_id) return setClientError("Choose a locality.");
    if ((f.latitude && !f.longitude) || (!f.latitude && f.longitude)) return setClientError("Enter both latitude and longitude, or neither.");
    if (!existing && !consent) return setClientError("Please confirm consent to store and publish this information.");

    const { price_text: _p, locality_id, ...rest } = f;
    void _p;
    const body: ListingInput = {
      ...rest,
      asking_price_inr: String(price),
      locality_id: Number(locality_id),
      plot_width_ft: blankToNull(f.plot_width_ft),
      plot_length_ft: blankToNull(f.plot_length_ft),
      road_frontage_ft: blankToNull(f.road_frontage_ft),
      latitude: blankToNull(f.latitude),
      longitude: blankToNull(f.longitude),
      general_address: blankToNull(f.general_address),
      restriction_notes: blankToNull(f.restriction_notes),
      additional_notes: blankToNull(f.additional_notes),
      relevant_authorities: blankToNull(f.relevant_authorities),
    };
    const declarations = docList.map((d) => ({ document_type: d, availability: docs[d] ?? "unknown" }));
    setBusy(true);
    try {
      let saved: PropertyDetail;
      if (existing) {
        saved = await api.updateProperty(existing.id, body);
        saved = await api.setDocuments(existing.id, declarations);
      } else {
        saved = await api.createProperty({ ...body, documents: declarations, consent_to_store: true });
      }
      onSaved(saved);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-6">
      <Card className="space-y-4 p-5">
        <h2 className="font-semibold">Basic details</h2>
        <Field label="Title" htmlFor="title" required>
          <Input id="title" required minLength={5} maxLength={160} value={f.title} onChange={(e) => set("title", e.target.value)} placeholder="e.g. 30×40 east-facing plot in Saptapur" />
        </Field>
        <Field label="Description" htmlFor="description">
          <Textarea id="description" rows={4} maxLength={5000} value={f.description} onChange={(e) => set("description", e.target.value)} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Property type" htmlFor="ptype" required>
            <EnumSelect id="ptype" group="PropertyType" value={f.property_type} onChange={(v) => changeType(v as PropertyType)} />
          </Field>
          <Field label="Asking price (₹)" htmlFor="price" required hint="Digits, lakh or crore, e.g. 18.4 lakh">
            <Input id="price" required value={f.price_text} onChange={(e) => set("price_text", e.target.value)} />
          </Field>
        </div>
      </Card>

      <Card className="space-y-4 p-5">
        <h2 className="font-semibold">Location</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Locality" htmlFor="locality" required>
            <Select id="locality" required value={f.locality_id} onChange={(e) => set("locality_id", e.target.value)}>
              <option value="">Choose…</option>
              {localities.map((l) => <option key={l.id} value={l.id}>{l.locality_name} ({l.city})</option>)}
            </Select>
          </Field>
          <Field label="General address" htmlFor="addr" hint="Avoid exact door numbers; this is shown publicly.">
            <Input id="addr" maxLength={300} value={f.general_address ?? ""} onChange={(e) => set("general_address", e.target.value)} />
          </Field>
          <Field label="Latitude" htmlFor="lat" hint="Optional, e.g. 15.4589">
            <Input id="lat" inputMode="decimal" value={f.latitude ?? ""} onChange={(e) => set("latitude", e.target.value)} />
          </Field>
          <Field label="Longitude" htmlFor="lng" hint="Optional, e.g. 75.0078">
            <Input id="lng" inputMode="decimal" value={f.longitude ?? ""} onChange={(e) => set("longitude", e.target.value)} />
          </Field>
        </div>
      </Card>

      <Card className="space-y-4 p-5">
        <h2 className="font-semibold">Size and access</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Area" htmlFor="area" required hint={sqft ? `= ${formatSqft(sqft)}` : undefined}>
            <Input id="area" required inputMode="decimal" value={f.area_value} onChange={(e) => set("area_value", e.target.value)} />
          </Field>
          <Field label="Unit" htmlFor="unit">
            <EnumSelect id="unit" group="AreaUnit" value={f.area_unit} onChange={(v) => set("area_unit", v as FormState["area_unit"])} />
          </Field>
          <Field label="Road access" htmlFor="road">
            <EnumSelect id="road" group="RoadAccess" value={f.road_access} onChange={(v) => set("road_access", v as FormState["road_access"])} />
          </Field>
          {isPlot && (
            <>
              <Field label="Width (ft)" htmlFor="w"><Input id="w" inputMode="decimal" value={f.plot_width_ft ?? ""} onChange={(e) => set("plot_width_ft", e.target.value)} /></Field>
              <Field label="Length (ft)" htmlFor="l"><Input id="l" inputMode="decimal" value={f.plot_length_ft ?? ""} onChange={(e) => set("plot_length_ft", e.target.value)} /></Field>
            </>
          )}
          <Field label="Road frontage (ft)" htmlFor="front"><Input id="front" inputMode="decimal" value={f.road_frontage_ft ?? ""} onChange={(e) => set("road_frontage_ft", e.target.value)} /></Field>
        </div>
        {isPlot && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={!!f.is_corner_plot} onChange={(e) => set("is_corner_plot", e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-700" />
            Corner plot
          </label>
        )}
      </Card>

      <Card className="space-y-4 p-5">
        <div>
          <h2 className="font-semibold">Land and legal information</h2>
          <p className="text-sm text-slate-500">Declare what you know. Buyers see these as your claims, not as verified facts.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Land classification" htmlFor="lc"><EnumSelect id="lc" group="LandClassification" value={f.land_classification} onChange={(v) => set("land_classification", v)} /></Field>
          <Field label="Intended use" htmlFor="use"><EnumSelect id="use" group="IntendedLandUse" value={f.intended_land_use} onChange={(v) => set("intended_land_use", v)} /></Field>
          <Field label="Conversion (DC) status" htmlFor="conv"><EnumSelect id="conv" group="ConversionStatus" value={f.conversion_status} onChange={(v) => set("conversion_status", v)} /></Field>
          <Field label="Layout approval" htmlFor="layout"><EnumSelect id="layout" group="LayoutApprovalStatus" value={f.layout_approval_status} onChange={(v) => set("layout_approval_status", v)} /></Field>
          <Field label="Relevant authorities" htmlFor="auth" hint="e.g. planning authority, municipal corporation"><Input id="auth" maxLength={300} value={f.relevant_authorities ?? ""} onChange={(e) => set("relevant_authorities", e.target.value)} /></Field>
          <Field label="Restrictions or uncertainties" htmlFor="restr"><Input id="restr" maxLength={2000} value={f.restriction_notes ?? ""} onChange={(e) => set("restriction_notes", e.target.value)} /></Field>
        </div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium text-slate-700">Documents you have</legend>
          <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {docList.map((d) => (
              <div key={d} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <span className="text-sm">{meta?.enums.DocumentType?.[d] ?? d}</span>
                <Select aria-label={`${d} availability`} className="w-44" value={docs[d] ?? "unknown"} onChange={(e) => setDocs({ ...docs, [d]: e.target.value as DocumentAvailability })}>
                  <option value="provided">I have it</option>
                  <option value="not_provided">I don&rsquo;t have it</option>
                  <option value="unknown">Not sure</option>
                  <option value="not_applicable">Not applicable</option>
                </Select>
              </div>
            ))}
          </div>
          <p className="mt-1 text-xs text-slate-500">Document file upload is not part of this prototype; only your declaration is stored.</p>
        </fieldset>
      </Card>

      <Card className="space-y-3 p-5">
        <h2 className="font-semibold">Nearby amenities</h2>
        <div className="grid gap-2 sm:grid-cols-3">
          {(meta?.amenities ?? []).map((a) => (
            <label key={a.code} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-700"
                checked={f.amenities.includes(a.code)}
                onChange={(e) => set("amenities", e.target.checked ? [...f.amenities, a.code] : f.amenities.filter((x) => x !== a.code))}
              />
              {a.label}
            </label>
          ))}
        </div>
      </Card>

      {!existing && (
        <label className="flex items-start gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-700" />
          I consent to PropWise storing this information and publishing it after admin review. I confirm I am entitled to list this property.
        </label>
      )}

      {clientError && <Alert tone="red">{clientError}</Alert>}
      {error && (
        <Alert tone="red" title={error.message}>
          {error.details?.length > 0 && <ul className="list-disc pl-4">{error.details.map((d, i) => <li key={i}>{d.field ?? "form"}: {d.issue}</li>)}</ul>}
        </Alert>
      )}
      <div className="flex items-center gap-3">
        <Button type="submit" loading={busy}>{existing ? "Save changes" : "Submit for review"}</Button>
        <p className="text-sm text-slate-500">{existing ? "Edits to a published listing send it back for admin review." : "New listings stay hidden until an admin approves them."}</p>
      </div>
    </form>
  );
}
