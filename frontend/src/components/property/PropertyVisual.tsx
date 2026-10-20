import { mediaUrl } from "@/lib/api";
import type { PropertyType } from "@/lib/types";
import { cx } from "@/components/ui";

const TINT: Record<PropertyType, string> = {
  residential_plot: "from-brand-100 to-brand-50 text-brand-700",
  independent_house: "from-sky-100 to-sky-50 text-sky-700",
  agricultural_land: "from-lime-100 to-lime-50 text-lime-700",
  commercial_plot: "from-amber-100 to-amber-50 text-amber-700",
  commercial_building: "from-orange-100 to-orange-50 text-orange-700",
};

/** Line illustration for a property type; also used on the home page category tiles. */
export function CategoryIcon({ type, className = "h-14 w-14" }: { type: PropertyType; className?: string }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.5, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  switch (type) {
    case "agricultural_land":
      return <svg viewBox="0 0 48 48" className={className} {...common}><path d="M4 36h40M8 36c4-10 8-14 16-14s12 4 16 14M24 22V10M24 14c-3-3-6-3-8-2M24 12c3-3 6-3 8-2" /></svg>;
    case "independent_house":
      return <svg viewBox="0 0 48 48" className={className} {...common}><path d="M6 22 24 8l18 14M10 19v19h28V19M20 38V27h8v11" /></svg>;
    case "commercial_building":
      return <svg viewBox="0 0 48 48" className={className} {...common}><path d="M8 40V12h20v28M28 20h12v20M14 18h2M20 18h2M14 24h2M20 24h2M14 30h2M20 30h2M33 26h2M33 32h2M4 40h40" /></svg>;
    default:
      return <svg viewBox="0 0 48 48" className={className} {...common}><path d="M6 34 18 14l24 6-8 18z" strokeDasharray="3 3" /><path d="M18 14v-6M18 8l6 2-6 2" /></svg>;
  }
}

/** Real photo if the seller uploaded one, otherwise a neutral illustration (never a fake photo). */
export function PropertyVisual({ type, image, className }: { type: PropertyType; image?: string | null; className?: string }) {
  const src = mediaUrl(image ?? null);
  if (src) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt="Property photo uploaded by the seller" className={cx("h-full w-full object-cover", className)} />;
  }
  return (
    <div className={cx("flex h-full w-full flex-col items-center justify-center bg-gradient-to-br", TINT[type], className)}>
      <CategoryIcon type={type} />
      <span className="mt-1 text-[11px] font-medium opacity-70">No photo provided</span>
    </div>
  );
}
