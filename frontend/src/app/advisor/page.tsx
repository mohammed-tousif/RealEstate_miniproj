"use client";

import { useEffect, useState } from "react";
import { EMPTY_PREFERENCES, loadPreferences, storePreferences } from "@/lib/advisor";
import { api, ApiError } from "@/lib/api";
import { formatINRShort, parseINR } from "@/lib/format";
import { useAuth, useMeta } from "@/lib/providers";
import type { AreaUnit, FactorName, Importance, Locality, Objective, Preferences, PropertyType, RecommendationResponse } from "@/lib/types";
import { Button, Card, Disclosure, EmptyState, Field, Input, Note, PageHeader, Select, Skeleton } from "@/components/ui";
import { RecommendationCard } from "@/components/advisor/RecommendationCard";

const OBJECTIVES: Record<Objective, string> = {
  build_house: "Build a house",
  long_term_investment: "Long-term investment",
  farming: "Farming",
  commercial_use: "Commercial use",
};
const FACTORS: [FactorName, string][] = [
  ["budget", "Budget fit"],
  ["location", "Location"],
  ["purpose", "Suits my purpose"],
  ["connectivity", "Road access"],
  ["documentation", "Documents declared"],
];
const IMPORTANCE: [Importance, string][] = [
  ["very_important", "Very important"],
  ["important", "Important"],
  ["somewhat", "Somewhat"],
  ["not_important", "Doesn't matter"],
];
const DEMO: Preferences = {
  ...EMPTY_PREFERENCES,
  max_budget: "2500000",
  property_types: ["residential_plot"],
  cities: ["Hubballi", "Dharwad"],
  objective: "long_term_investment",
};

const lakh = (v: string | null | undefined) => (v ? `${Number(v) / 1e5} lakh` : "");

function Check({ checked, onChange, children }: { checked: boolean; onChange: (v: boolean) => void; children: React.ReactNode }) {
  return (
    <label className="flex items-center gap-2 text-sm text-slate-700">
      <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-brand-700 focus:ring-brand-500" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  );
}

const toggle = <T,>(list: T[], v: T, on: boolean) => (on ? [...list, v] : list.filter((x) => x !== v));

export default function AdvisorPage() {
  const meta = useMeta();
  const { user } = useAuth();
  const [p, setP] = useState<Preferences>(EMPTY_PREFERENCES);
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [localities, setLocalities] = useState<Locality[]>([]);
  const [res, setRes] = useState<RecommendationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const adopt = (prefs: Preferences) => {
    setP(prefs);
    setBudgetMin(lakh(prefs.min_budget));
    setBudgetMax(lakh(prefs.max_budget));
  };

  useEffect(() => {
    api.localities().then(setLocalities).catch(() => setLocalities([]));
    const local = loadPreferences();
    if (local) adopt(local);
  }, []);

  useEffect(() => {
    if (!user || loadPreferences()) return;
    api.getPreferences().then((r) => r?.other?.advisor && adopt({ ...EMPTY_PREFERENCES, ...r.other.advisor })).catch(() => undefined);
  }, [user]);

  const set = <K extends keyof Preferences>(k: K, v: Preferences[K]) => setP((prev) => ({ ...prev, [k]: v }));

  const build = (): Preferences | null => {
    const mn = budgetMin.trim() ? parseINR(budgetMin) : null;
    const mx = budgetMax.trim() ? parseINR(budgetMax) : null;
    if ((budgetMin.trim() && !mn) || (budgetMax.trim() && !mx)) {
      setError("Budget not understood. Try 2500000, 25 lakh or 1.2 crore.");
      return null;
    }
    if (mn && mx && mn > mx) {
      setError("Minimum budget is higher than maximum budget.");
      return null;
    }
    if (p.min_area_value && !(Number(p.min_area_value) > 0)) {
      setError("Minimum area must be a number greater than zero.");
      return null;
    }
    return { ...p, min_budget: mn ? String(mn) : null, max_budget: mx ? String(mx) : null, min_area_value: p.min_area_value || null };
  };

  const run = async (prefs: Preferences | null = build()) => {
    if (!prefs) return;
    setError(null);
    setBusy(true);
    storePreferences(prefs);
    try {
      setRes(await api.recommend(prefs, 10));
    } catch (e) {
      setRes(null);
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    const prefs = build();
    if (!prefs) return;
    try {
      await api.savePreferences(prefs);
      setSaved("Saved to your account.");
    } catch (e) {
      setSaved((e as ApiError).message);
    }
  };

  const shownLocalities = localities.filter((l) => p.cities.length === 0 || p.cities.includes(l.city as "Hubballi" | "Dharwad") || p.locality_ids.includes(l.id));

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 md:py-14">
      <PageHeader
        title="Property advisor"
        subtitle="Tell us what you need. Strict requirements filter listings out; everything else is weighed into a suitability score you can inspect."
        actions={<Button variant="secondary" size="sm" onClick={() => { adopt(DEMO); run(DEMO); }}>Try the demo: ₹25 lakh plot</Button>}
      />
      <div className="grid gap-10 lg:grid-cols-[360px_1fr]">
        <Card className="h-fit p-6 lg:sticky lg:top-24">
          <form className="space-y-6" aria-label="Advisor preferences" onSubmit={(e) => { e.preventDefault(); run(); }}>
            <fieldset className="space-y-2">
              <legend className="mb-1 text-sm font-semibold text-ink-900">Budget</legend>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Minimum" htmlFor="adv-min"><Input id="adv-min" placeholder="optional" value={budgetMin} onChange={(e) => setBudgetMin(e.target.value)} /></Field>
                <Field label="Maximum" htmlFor="adv-max"><Input id="adv-max" placeholder="e.g. 25 lakh" value={budgetMax} onChange={(e) => setBudgetMax(e.target.value)} /></Field>
              </div>
              <Check checked={p.budget_strict} onChange={(v) => set("budget_strict", v)}>Strict (otherwise up to 10% over is allowed)</Check>
            </fieldset>

            <Field label="What is it for?" htmlFor="adv-objective">
              <Select id="adv-objective" value={p.objective ?? ""} onChange={(e) => set("objective", (e.target.value || null) as Objective | null)}>
                <option value="">Not specified</option>
                {Object.entries(OBJECTIVES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </Select>
            </Field>

            <fieldset className="space-y-1">
              <legend className="mb-1 text-sm font-semibold text-ink-900">Property type</legend>
              {Object.entries(meta?.enums.PropertyType ?? {}).map(([k, v]) => (
                <Check key={k} checked={p.property_types.includes(k as PropertyType)} onChange={(on) => set("property_types", toggle(p.property_types, k as PropertyType, on))}>{v}</Check>
              ))}
              <div className="pt-1"><Check checked={p.types_strict} onChange={(v) => set("types_strict", v)}>Only these types</Check></div>
            </fieldset>

            <fieldset className="space-y-1">
              <legend className="mb-1 text-sm font-semibold text-ink-900">Location</legend>
              <div className="flex gap-4">
                {(["Hubballi", "Dharwad"] as const).map((c) => (
                  <Check key={c} checked={p.cities.includes(c)} onChange={(on) => set("cities", toggle(p.cities, c, on))}>{c}</Check>
                ))}
              </div>
              <details className="rounded-design border border-slate-200 px-3 py-2">
                <summary className="cursor-pointer text-sm text-ink-700">Preferred localities ({p.locality_ids.length})</summary>
                <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                  {shownLocalities.map((l) => (
                    <Check key={l.id} checked={p.locality_ids.includes(l.id)} onChange={(on) => set("locality_ids", toggle(p.locality_ids, l.id, on))}>
                      {l.locality_name} <span className="text-slate-400">({l.city})</span>
                    </Check>
                  ))}
                </div>
              </details>
              <Check checked={p.location_strict} onChange={(v) => set("location_strict", v)}>Only these areas</Check>
            </fieldset>

            <fieldset className="space-y-2">
              <legend className="mb-1 text-sm font-semibold text-ink-900">Minimum area</legend>
              <div className="grid grid-cols-[1fr_100px] gap-2">
                <Input aria-label="Minimum area" inputMode="decimal" placeholder="optional" value={p.min_area_value ?? ""} onChange={(e) => set("min_area_value", e.target.value)} />
                <Select aria-label="Minimum area unit" value={p.min_area_unit} onChange={(e) => set("min_area_unit", e.target.value as AreaUnit)}>
                  <option value="sqft">sq ft</option><option value="sqm">sq m</option><option value="gunta">gunta</option><option value="acre">acre</option>
                </Select>
              </div>
              <Check checked={p.area_strict} onChange={(v) => set("area_strict", v)}>Strict</Check>
            </fieldset>

            <Disclosure summary="Fine-tune what matters most">
              <fieldset className="space-y-2">
              <legend className="sr-only">How much does each matter?</legend>
              {FACTORS.map(([f, text]) => (
                <div key={f} className="grid grid-cols-[1fr_140px] items-center gap-2">
                  <label htmlFor={`imp-${f}`} className="text-sm text-slate-700">{text}</label>
                  <Select id={`imp-${f}`} value={p.importance[f] ?? "important"} onChange={(e) => set("importance", { ...p.importance, [f]: e.target.value as Importance })}>
                    {IMPORTANCE.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </Select>
                </div>
              ))}
              </fieldset>
            </Disclosure>

            {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" loading={busy} className="flex-1">Find matches</Button>
              <Button type="button" variant="secondary" onClick={() => { adopt(EMPTY_PREFERENCES); storePreferences(null); setRes(null); }}>Reset</Button>
            </div>
            {user && <Button type="button" variant="secondary" size="sm" onClick={save} className="w-full">Save to my account</Button>}
            {saved && <p className="text-xs text-slate-500">{saved}</p>}
          </form>
        </Card>

        <section aria-label="Recommendations" className="min-w-0 space-y-6">
          {busy && !res ? (
            <Skeleton className="h-64 w-full" />
          ) : !res ? (
            <EmptyState title="Your matches will appear here">
              Each result shows its score, what it is based on, the trade-offs and what to verify yourself. Try the demo if you are not sure where to start.
            </EmptyState>
          ) : (
            <>
              <div className="rounded-2xl border border-slate-200/70 bg-white p-5 text-sm leading-6 text-ink-700 shadow-card">
                <p>
                  <span className="font-semibold">{res.matched}</span> of {res.candidates_considered} approved listings meet your strict requirements
                  {res.matched > res.results.length && `; showing the top ${res.results.length}`}.
                  {p.max_budget && ` Budget up to ${formatINRShort(p.max_budget)}.`}
                </p>
                {res.excluded.length > 0 && (
                  <p className="mt-1 text-slate-500">Excluded: {res.excluded.map((e) => `${e.reason.toLowerCase()} (${e.count})`).join(", ")}.</p>
                )}
                {res.notes.length > 0 && <ul className="mt-1 list-disc pl-5 text-slate-500">{res.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
                <p className="mt-2 text-xs text-slate-500">{res.score_label} Engine {res.engine_version}.</p>
              </div>
              {res.is_synthetic_data && <Note>Listings marked synthetic are demonstration data, so matches among them illustrate the method, not real opportunities. Listings marked real are unverified third-party asking prices.</Note>}
              {res.results.length === 0 ? (
                <EmptyState title="No listings meet all of your strict requirements">
                  Relax the requirement with the most exclusions above, or untick its &ldquo;strict&rdquo; box so it is weighed instead of enforced.
                </EmptyState>
              ) : (
                res.results.map((r) => <RecommendationCard key={r.property.id} r={r} />)
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
