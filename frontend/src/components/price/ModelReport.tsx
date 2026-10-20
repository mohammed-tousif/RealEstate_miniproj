"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatINRShort } from "@/lib/format";
import type { ModelInfo, ModelMetrics } from "@/lib/types";
import { Skeleton } from "@/components/ui";

const NAMES: Record<string, string> = {
  baseline_median: "Baseline: overall median price",
  baseline_locality_type_ppsf: "Baseline: locality + type median ₹/sq ft × area",
  linear_regression: "Linear Regression",
  random_forest: "Random Forest",
  gradient_boosting: "Gradient Boosting",
};
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

function MetricsTable({ rows, caption }: { rows: [string, ModelMetrics][]; caption: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-sm">
        <caption className="mb-2 text-left text-xs text-slate-500">{caption}</caption>
        <thead className="text-xs uppercase text-slate-500">
          <tr><th className="py-1 pr-3">Model</th><th className="pr-3">MAE</th><th className="pr-3">MAPE</th><th className="pr-3">Median APE</th><th>R²</th></tr>
        </thead>
        <tbody>
          {rows.map(([k, m]) => (
            <tr key={k} className="border-t border-slate-100">
              <td className="py-1.5 pr-3">{NAMES[k] ?? k}</td>
              <td className="pr-3">{formatINRShort(m.mae_inr)}</td>
              <td className="pr-3">{pct(m.mape)}</td>
              <td className="pr-3">{pct(m.median_ape)}</td>
              <td>{m.r2.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Live summary of the active price model, read from /model-info (numbers come from the training run). */
export function ModelReport() {
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api.modelInfo().then(setInfo).catch(() => setFailed(true));
  }, []);
  if (failed) return <p>The model report could not be loaded from the server.</p>;
  if (!info) return <Skeleton className="h-40 w-full" />;
  const m = info.price_model;
  if (!m) return <p>{info.message}</p>;
  return (
    <div className="space-y-4">
      <p>
        <strong>Target:</strong> the listed asking price (not a sale price), modelled on a log scale.{" "}
        <strong>Data:</strong> {m.dataset.clean_rows} cleaned rows out of {m.dataset.raw_rows}; {m.dataset.excluded_rows} were
        excluded (rejected listings, near-duplicate copies, typo-like price errors) and every exclusion is listed in the data-quality report.
      </p>
      <p>
        <strong>Split:</strong> {m.split.train} training, {m.split.validation} validation and {m.split.test} test listings. Re-listings of the same
        property are kept in one part so the model is never tested on something it has already seen. The model with the lowest
        validation error was chosen, and only then was it scored once on the test listings.
      </p>
      <MetricsTable caption="Validation listings (used to choose the model)" rows={Object.entries(m.validation_metrics)} />
      <MetricsTable caption={`Test listings (n = ${m.split.test}), scored once after the choice`} rows={Object.entries(m.test_metrics)} />
      <p>
        <strong>Chosen:</strong> {m.model_label} (version {m.model_version}). <strong>Range:</strong> {m.interval.method}; it should hold
        about {pct(m.interval.nominal)} of prices and held {pct(m.interval.measured_test_coverage)} of the {m.interval.test_n} test listings.
      </p>
      <MetricsTable caption="Localities never seen in training (5-fold, grouped by locality)" rows={Object.entries(m.locality_holdout.results)} />
      {(() => {
        const r = m.locality_holdout.results;
        const base = r.baseline_locality_type_ppsf;
        const mine = r[m.model_name];
        return base && mine ? (
          <p>
            For localities it has never seen, the model is {mine.mae_inr > base.mae_inr ? "less accurate than the simple baseline" : "still better than the simple baseline"}
            {" "}({formatINRShort(mine.mae_inr)} vs {formatINRShort(base.mae_inr)} average error). Estimates for a locality with no
            training data carry a warning.
          </p>
        ) : null;
      })()}
      <p>
        MAE is the average rupee error; MAPE and median APE are the average and typical percentage error. R² is on rupee values, so a few
        large farmland prices dominate it.
      </p>
      <p className="rounded-lg bg-amber-50 p-3 text-amber-900">{m.caveat}</p>
    </div>
  );
}
