"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { defaultsForType } from "@/lib/documents";
import { formatSqft, parseINR, toSqft } from "@/lib/format";
import { useMeta } from "@/lib/providers";
import type { AreaUnit, Locality, PriceEstimate, PriceEstimateInput, PropertyType, RoadAccess } from "@/lib/types";
import { Alert, Button, Card, Disclosure, EmptyState, Field, Input, Note, PageHeader, Select } from "@/components/ui";
import { EstimateResult } from "@/components/price/EstimateResult";

type Form = {
  locality_id: string;
  property_type: PropertyType;
  area_value: string;
  area_unit: AreaUnit;
  land_classification: string;
  conversion_status: string;
  layout_approval_status: string;
  road_access: RoadAccess;
  road_frontage_ft: string;
  is_corner_plot: "" | "yes" | "no";
  quoted: string;
};

const INITIAL: Form = {
  locality_id: "",
  property_type: "residential_plot",
  area_value: "",
  area_unit: "sqft",
  ...(defaultsForType("residential_plot") as { land_classification: string; conversion_status: string; layout_approval_status: string }),
  road_access: "unknown",
  road_frontage_ft: "",
  is_corner_plot: "",
  quoted: "",
};

function EnumSelect({ id, group, value, onChange }: { id: string; group: string; value: string; onChange: (v: string) => void }) {
  const meta = useMeta();
  return (
    <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      {Object.entries(meta?.enums[group] ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
    </Select>
  );
}

export default function EstimatePage() {
  const [f, setF] = useState<Form>(INITIAL);
  const [localities, setLocalities] = useState<Locality[]>([]);
  const [result, setResult] = useState<PriceEstimate | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.localities().then(setLocalities).catch(() => setLocalities([]));
  }, []);

  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF((p) => ({ ...p, [k]: v }));
  const changeType = (t: PropertyType) => {
    const d = defaultsForType(t);
    setF((p) => ({ ...p, property_type: t, land_classification: d.land_classification, conversion_status: d.conversion_status,
      layout_approval_status: d.layout_approval_status, area_unit: t === "agricultural_land" ? "acre" : p.area_unit === "acre" ? "sqft" : p.area_unit }));
  };
  const sqft = f.area_value && Number(f.area_value) > 0 ? toSqft(Number(f.area_value), f.area_unit) : null;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);
    setError(null);
    if (!f.locality_id) return setClientError("Choose a locality.");
    if (!sqft) return setClientError("Enter an area greater than zero.");
    let quoted: number | null = null;
    if (f.quoted.trim()) {
      quoted = parseINR(f.quoted);
      if (!quoted) return setClientError("Quoted price not understood. Try 2500000, 25 lakh or 1.2 crore.");
    }
    const body: PriceEstimateInput = {
      locality_id: Number(f.locality_id),
      property_type: f.property_type,
      area_value: f.area_value.trim(),
      area_unit: f.area_unit,
      land_classification: f.land_classification,
      conversion_status: f.conversion_status,
      layout_approval_status: f.layout_approval_status,
      road_access: f.road_access,
      ...(f.road_frontage_ft.trim() ? { road_frontage_ft: f.road_frontage_ft.trim() } : {}),
      ...(f.is_corner_plot ? { is_corner_plot: f.is_corner_plot === "yes" } : {}),
      ...(quoted ? { asking_price_inr: String(quoted) } : {}),
    };
    setBusy(true);
    try {
      setResult(await api.estimatePrice(body));
    } catch (err) {
      setResult(null);
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  };

  const farmland = f.property_type === "agricultural_land";
  const isPlot = f.property_type === "residential_plot" || f.property_type === "commercial_plot";

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 md:py-14">
      <PageHeader
        title="Indicative price estimate"
        subtitle="A machine-learning estimate of a typical asking price for a property like this, with a range and comparable listings. It is not a valuation."
      />
      <div className="grid gap-10 lg:grid-cols-[380px_1fr]">
        <Card className="h-fit p-6">
          <form onSubmit={submit} className="space-y-5" aria-label="Property details for estimate">
            <Field label="Locality" htmlFor="locality" required>
              <Select id="locality" value={f.locality_id} onChange={(e) => set("locality_id", e.target.value)}>
                <option value="">Choose a locality</option>
                {localities.map((l) => <option key={l.id} value={l.id}>{l.locality_name} ({l.city})</option>)}
              </Select>
            </Field>
            <Field label="Property type" htmlFor="ptype" required>
              <EnumSelect id="ptype" group="PropertyType" value={f.property_type} onChange={(v) => changeType(v as PropertyType)} />
            </Field>
            <Field label="Area" htmlFor="area" required hint={sqft ? `= ${formatSqft(sqft)}` : undefined}>
              <div className="grid grid-cols-[1fr_110px] gap-2">
                <Input id="area" inputMode="decimal" placeholder={farmland ? "e.g. 2.5" : "e.g. 1200"} value={f.area_value} onChange={(e) => set("area_value", e.target.value)} />
                <Select aria-label="Area unit" value={f.area_unit} onChange={(e) => set("area_unit", e.target.value as AreaUnit)}>
                  <option value="sqft">sq ft</option>
                  <option value="sqm">sq m</option>
                  <option value="gunta">gunta</option>
                  <option value="acre">acre</option>
                </Select>
              </div>
            </Field>
            <Disclosure summary="Land, legal and road details (optional)">
              <Field label="Land classification (as declared)" htmlFor="landclass">
                <EnumSelect id="landclass" group="LandClassification" value={f.land_classification} onChange={(v) => set("land_classification", v)} />
              </Field>
              {!farmland && (
                <Field label="Conversion status (as claimed)" htmlFor="conversion">
                  <EnumSelect id="conversion" group="ConversionStatus" value={f.conversion_status} onChange={(v) => set("conversion_status", v)} />
                </Field>
              )}
              {isPlot && (
                <Field label="Layout approval (as claimed)" htmlFor="layout">
                  <EnumSelect id="layout" group="LayoutApprovalStatus" value={f.layout_approval_status} onChange={(v) => set("layout_approval_status", v)} />
                </Field>
              )}
              <Field label="Road access" htmlFor="road">
                <EnumSelect id="road" group="RoadAccess" value={f.road_access} onChange={(v) => set("road_access", v as RoadAccess)} />
              </Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Road frontage (ft)" htmlFor="frontage">
                  <Input id="frontage" inputMode="decimal" placeholder="optional" value={f.road_frontage_ft} onChange={(e) => set("road_frontage_ft", e.target.value)} />
                </Field>
                {isPlot && (
                  <Field label="Corner plot" htmlFor="corner">
                    <Select id="corner" value={f.is_corner_plot} onChange={(e) => set("is_corner_plot", e.target.value as Form["is_corner_plot"])}>
                      <option value="">Not stated</option>
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </Select>
                  </Field>
                )}
              </div>
            </Disclosure>
            <Field label="Quoted price to compare (optional)" htmlFor="quoted" hint="e.g. 25 lakh">
              <Input id="quoted" value={f.quoted} onChange={(e) => set("quoted", e.target.value)} />
            </Field>
            {clientError && <p className="text-sm text-red-600" role="alert">{clientError}</p>}
            <Button type="submit" className="w-full" loading={busy}>Estimate price</Button>
          </form>
        </Card>

        <div>
          {error ? (
            error.status === 503 ? (
              <EmptyState title="Price model not available">{error.message}</EmptyState>
            ) : (
              <Alert tone="red" title="Could not estimate">
                {error.message}
                {error.details.length > 0 && <ul className="mt-1 list-disc pl-5">{error.details.map((d) => <li key={`${d.field}${d.issue}`}>{d.field}: {d.issue}</li>)}</ul>}
              </Alert>
            )
          ) : result ? (
            <Card className="p-6"><EstimateResult e={result} /></Card>
          ) : (
            <EmptyState title="Enter the property details">
              The estimate, an indicative range, comparable listings and any warnings about the input will appear here.
            </EmptyState>
          )}
          <Note className="mt-6">
            The model was trained mostly on synthetic demonstration data (plus a few real asking prices), so it mainly reflects the
            rules used to generate that data, not the real Hubballi–Dharwad market. See the Methodology page for how it was tested.
          </Note>
        </div>
      </div>
    </div>
  );
}
