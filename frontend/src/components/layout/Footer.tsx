import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 text-sm text-slate-600 md:grid-cols-3">
        <div>
          <p className="font-semibold text-slate-900">PropWise AI</p>
          <p className="mt-1">An academic prototype for property research in Hubballi–Dharwad, Karnataka.</p>
        </div>
        <div>
          <p className="font-semibold text-slate-900">About the data</p>
          <p className="mt-1">
            Listings shown in this demo are <strong>synthetic</strong>. They are not real properties for sale and their
            prices are not market data.
          </p>
        </div>
        <div>
          <p className="font-semibold text-slate-900">Disclaimer</p>
          <p className="mt-1">
            Not legal or financial advice. Document statuses reflect seller declarations; verify independently.{" "}
            <Link href="/about" className="text-brand-700 underline">Methodology</Link>
          </p>
        </div>
      </div>
    </footer>
  );
}
