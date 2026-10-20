import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 rounded-tl-[60px] bg-ink-gradient text-white md:rounded-tl-[108px]">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 text-sm text-ink-400 md:grid-cols-3">
        <div>
          <p className="text-base font-medium text-white">PropWise AI</p>
          <p className="mt-1">An academic prototype for property research in Hubballi–Dharwad, Karnataka.</p>
        </div>
        <div>
          <p className="text-base font-medium text-white">About the data</p>
          <p className="mt-1">
            Most listings in this demo are <strong className="text-white">synthetic</strong>: not real properties, and their prices are not market
            data. A few are marked <strong className="text-white">real</strong>: land listings copied from a public website with their source link,
            not verified by PropWise.
          </p>
        </div>
        <div>
          <p className="text-base font-medium text-white">Disclaimer</p>
          <p className="mt-1">
            Not legal or financial advice. Document statuses reflect seller declarations; verify independently.{" "}
            <Link href="/about" className="text-white underline">Methodology</Link>
          </p>
        </div>
      </div>
    </footer>
  );
}
