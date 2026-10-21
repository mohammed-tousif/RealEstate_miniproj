import Link from "next/link";

const LINKS = [
  { href: "/properties", label: "Explore" },
  { href: "/advisor", label: "Advisor" },
  { href: "/chat", label: "Assistant" },
  { href: "/estimate", label: "Price estimate" },
  { href: "/compare", label: "Compare" },
  { href: "/about", label: "Methodology" },
];

export function Footer() {
  return (
    <footer className="mt-24 rounded-tl-[60px] bg-ink-gradient text-white md:rounded-tl-[108px]">
      <div className="mx-auto max-w-7xl px-4 pb-10 pt-14">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <p className="text-lg font-semibold">PropWise <span className="text-brand-200">AI</span></p>
            <p className="mt-2 text-sm leading-6 text-ink-400">Explainable property research for Hubballi–Dharwad, Karnataka. An academic prototype.</p>
          </div>
          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-10 gap-y-2 text-sm sm:grid-cols-3">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} className="text-ink-400 transition hover:text-white">{l.label}</Link>
            ))}
          </nav>
        </div>
        <p className="mt-12 border-t border-white/10 pt-6 text-xs leading-5 text-ink-500">
          Most listings are <strong className="font-medium text-ink-400">synthetic</strong> demo data, not real properties or market prices. Listings marked{" "}
          <strong className="font-medium text-ink-400">real</strong> are copied from a public website and unverified. Document statuses are seller declarations.
          Not legal or financial advice.
        </p>
      </div>
    </footer>
  );
}
