import { cx } from "@/components/ui";

/** Share of applicable documents the seller declared as provided. Says nothing about legal validity. */
export function DocMeter({ provided, applicable, score, compact }: { provided: number; applicable: number; score: number; compact?: boolean }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.75 ? "bg-emerald-500" : score >= 0.45 ? "bg-amber-500" : "bg-red-500";
  return (
    <div title="Documents the seller declared as provided (not verified)">
      <div className={cx("flex items-center justify-between text-xs", compact ? "text-slate-600" : "text-slate-700")}>
        <span>{provided} of {applicable} documents declared</span>
        {!compact && <span className="font-medium">{pct}%</span>}
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label="Documentation completeness">
        <div className={cx("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
