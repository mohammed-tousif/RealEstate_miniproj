"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { parseINR, toSqft } from "@/lib/format";
import { useMeta } from "@/lib/providers";
import type { Locality } from "@/lib/types";
import { Button, Field, Input, Select } from "@/components/ui";

export type Filters = Record<string, string | string[]>;

const KEY_DOCS = ["rtc_pahani", "encumbrance_certificate", "sale_deed", "khata", "dc_conversion_order", "layout_approval"];

function CheckGroup({ name, options, value, onChange }: { name: string; options: Record<string, string>; value: string[]; onChange: (v: string[]) => void }) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-medium text-slate-700">{name}</legend>
      <div className="space-y-1">
        {Object.entries(options).map(([code, text]) => (
          <label key={code} className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-brand-700 focus:ring-brand-500"
              checked={value.includes(code)}
              onChange={(e) => onChange(e.target.checked ? [...value, code] : value.filter((v) => v !== code))}
            />
            {text}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

const arr = (v: string | string[] | undefined) => (Array.isArray(v) ? v : v ? [v] : []);
const str = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] ?? "" : v ?? "");

/** Budget is typed in lakh-friendly text; area in any unit. Both are converted before hitting the API. */
export function FilterSidebar({ initial, onApply, onReset }: { initial: Filters; onApply: (f: Filters) => void; onReset: () => void }) {
  const meta = useMeta();
  const [localities, setLocalities] = useState<Locality[]>([]);
  const [f, setF] = useState<Filters>(initial);
  const [budgetMin, setBudgetMin] = useState(str(initial.min_price) ? String(Number(initial.min_price) / 1e5) + " lakh" : "");
  const [budgetMax, setBudgetMax] = useState(str(initial.max_price) ? String(Number(initial.max_price) / 1e5) + " lakh" : "");
  const [areaUnit, setAreaUnit] = useState("sqft");
  const [areaMin, setAreaMin] = useState(str(initial.min_area_sqft));
  const [areaMax, setAreaMax] = useState(str(initial.max_area_sqft));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setF(initial), [initial]);
  useEffect(() => {
    api.localities().then(setLocalities).catch(() => setLocalities([]));
  }, []);

  const set = (k: string, v: string | string[]) => setF((prev) => ({ ...prev, [k]: v }));
  const enums = meta?.enums ?? {};
  const city = str(f.city);

  function apply(e: React.FormEvent) {
    e.preventDefault();
    const minP = budgetMin ? parseINR(budgetMin) : null;
    const maxP = budgetMax ? parseINR(budgetMax) : null;
    if ((budgetMin && minP === null) || (budgetMax && maxP === null)) {
      setError("Budget not understood. Try 2500000, 25 lakh or 1.2 crore.");
      return;
    }
    if (minP !== null && maxP !== null && minP > maxP) {
      setError("Minimum budget is higher than maximum budget.");
      return;
    }
    const toS = (v: string) => (v ? String(Math.round(toSqft(Number(v), areaUnit))) : "");
    if ((areaMin && Number.isNaN(Number(areaMin))) || (areaMax && Number.isNaN(Number(areaMax)))) {
      setError("Area must be a number.");
      return;
    }
    setError(null);
    onApply({ ...f, min_price: minP ? String(minP) : "", max_price: maxP ? String(maxP) : "", min_area_sqft: toS(areaMin), max_area_sqft: toS(areaMax), page: "1" });
  }

  return (
    <form onSubmit={apply} className="space-y-5" aria-label="Filters">
      <Field label="Search" htmlFor="q">
        <Input id="q" placeholder="Locality, title…" value={str(f.q)} onChange={(e) => set("q", e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Min budget" htmlFor="bmin">
          <Input id="bmin" placeholder="e.g. 10 lakh" value={budgetMin} onChange={(e) => setBudgetMin(e.target.value)} />
        </Field>
        <Field label="Max budget" htmlFor="bmax">
          <Input id="bmax" placeholder="e.g. 25 lakh" value={budgetMax} onChange={(e) => setBudgetMax(e.target.value)} />
        </Field>
      </div>
      <Field label="City" htmlFor="city">
        <Select id="city" value={city} onChange={(e) => setF((p) => ({ ...p, city: e.target.value, locality_id: "" }))}>
          <option value="">Hubballi and Dharwad</option>
          <option value="Hubballi">Hubballi</option>
          <option value="Dharwad">Dharwad</option>
        </Select>
      </Field>
      <Field label="Locality" htmlFor="locality">
        <Select id="locality" value={str(f.locality_id)} onChange={(e) => set("locality_id", e.target.value)}>
          <option value="">Any locality</option>
          {localities.filter((l) => !city || l.city === city).map((l) => (
            <option key={l.id} value={l.id}>{l.locality_name} ({l.city})</option>
          ))}
        </Select>
      </Field>
      {enums.PropertyType && <CheckGroup name="Property category" options={enums.PropertyType} value={arr(f.property_type)} onChange={(v) => set("property_type", v)} />}
      <div>
        <p className="mb-1.5 text-sm font-medium text-slate-700">Plot area</p>
        <div className="grid grid-cols-[1fr_1fr_96px] gap-2">
          <Input aria-label="Minimum area" placeholder="Min" inputMode="decimal" value={areaMin} onChange={(e) => setAreaMin(e.target.value)} />
          <Input aria-label="Maximum area" placeholder="Max" inputMode="decimal" value={areaMax} onChange={(e) => setAreaMax(e.target.value)} />
          <Select aria-label="Area unit" value={areaUnit} onChange={(e) => setAreaUnit(e.target.value)}>
            <option value="sqft">sq ft</option>
            <option value="sqm">sq m</option>
            <option value="gunta">gunta</option>
            <option value="acre">acre</option>
          </Select>
        </div>
      </div>
      {enums.LandClassification && <CheckGroup name="Land classification (as declared)" options={enums.LandClassification} value={arr(f.land_classification)} onChange={(v) => set("land_classification", v)} />}
      {enums.LayoutApprovalStatus && <CheckGroup name="Layout approval (as declared)" options={enums.LayoutApprovalStatus} value={arr(f.layout_approval_status)} onChange={(v) => set("layout_approval_status", v)} />}
      {enums.RoadAccess && <CheckGroup name="Road access" options={enums.RoadAccess} value={arr(f.road_access)} onChange={(v) => set("road_access", v)} />}
      {enums.IntendedLandUse && <CheckGroup name="Intended use" options={enums.IntendedLandUse} value={arr(f.intended_land_use)} onChange={(v) => set("intended_land_use", v)} />}
      {enums.DocumentType && (
        <CheckGroup
          name="Seller has declared"
          options={Object.fromEntries(KEY_DOCS.map((d) => [d, enums.DocumentType[d] ?? d]))}
          value={arr(f.has_document)}
          onChange={(v) => set("has_document", v)}
        />
      )}
      {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" className="flex-1">Apply filters</Button>
        <Button type="button" variant="secondary" onClick={() => { setBudgetMin(""); setBudgetMax(""); setAreaMin(""); setAreaMax(""); onReset(); }}>
          Reset
        </Button>
      </div>
    </form>
  );
}
