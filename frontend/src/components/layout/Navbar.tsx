"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth, useCompare } from "@/lib/providers";
import { cx } from "@/components/ui";

const LINKS = [
  { href: "/properties", label: "Explore" },
  { href: "/advisor", label: "Advisor" },
  { href: "/chat", label: "Assistant" },
  { href: "/estimate", label: "Price estimate" },
  { href: "/compare", label: "Compare" },
  { href: "/about", label: "Methodology" },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, ready } = useAuth();
  const { ids } = useCompare();
  const [open, setOpen] = useState(false);
  // On the home page the bar floats over the sky hero and turns solid once you scroll.
  const overHero = pathname === "/";
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    if (!overHero) return;
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [overHero]);
  const solid = !overHero || scrolled || open;

  const links = [
    ...LINKS,
    ...(user ? [{ href: "/favorites", label: "Favourites" }] : []),
    ...(user && (user.role === "seller" || user.role === "admin") ? [{ href: "/seller", label: "My listings" }] : []),
    ...(user?.role === "admin" ? [{ href: "/admin", label: "Admin" }] : []),
  ];

  const nav = (mobile: boolean) =>
    links.map((l) => {
      const active = pathname === l.href || pathname.startsWith(l.href + "/");
      return (
        <Link
          key={l.href}
          href={l.href}
          onClick={() => setOpen(false)}
          className={cx(
            "relative px-3 py-2 text-[15px] font-medium text-white transition",
            mobile
              ? cx("block rounded-md", active ? "bg-white/10" : "hover:bg-white/10")
              : cx(
                  "after:absolute after:inset-x-3 after:-bottom-[13px] after:h-[2px] after:rounded-full after:bg-white after:transition-opacity",
                  active ? "after:opacity-100" : "text-white/80 after:opacity-0 hover:text-white",
                ),
          )}
        >
          {l.label}
          {l.href === "/compare" && ids.length > 0 && (
            <span className="ml-1.5 rounded-full bg-white px-1.5 py-0.5 text-[10px] font-semibold text-ink-900">{ids.length}</span>
          )}
        </Link>
      );
    });

  return (
    <header
      className={cx(
        "z-[1000] text-white transition-colors duration-300",
        overHero ? "fixed inset-x-0 top-0" : "sticky top-0",
        solid ? "bg-ink-gradient shadow-float" : "bg-transparent",
      )}
    >
      <div className={cx("mx-auto flex h-16 max-w-7xl items-center gap-4 border-b px-4", solid ? "border-transparent" : "border-white/60")}>
        <Link href="/" className="flex items-center gap-2.5 text-lg font-bold leading-none tracking-tight">
          <svg viewBox="0 0 30 32" className="h-7 w-7" aria-hidden="true">
            <path d="M9 0h7L7 32H0z" fill="#fff" />
            <path d="M20 0h7l-9 32h-7z" fill="#fff" fillOpacity=".75" />
            <path d="M27 0h3l-9 32h-3z" fill="#80b2df" />
          </svg>
          <span>PropWise <span className="font-semibold text-brand-200">AI</span></span>
        </Link>
        <nav className="ml-4 hidden items-center gap-1 xl:flex">{nav(false)}</nav>
        <div className="ml-auto hidden items-center gap-3 xl:flex">
          {ready && !user && (
            <>
              <Link href="/login" className="flex items-center gap-1.5 px-2 py-2 text-[15px] font-medium hover:text-brand-100">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>
                Sign in
              </Link>
              <Link href="/register" className="flex items-center gap-1 rounded-design border border-white px-4 py-2 text-[15px] font-medium transition hover:bg-white hover:text-ink-900">
                Create account
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9" /></svg>
              </Link>
            </>
          )}
          {user && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-white/90">
                {user.name} <span className="text-xs text-white/60">({user.role})</span>
              </span>
              <button onClick={() => { logout(); router.push("/"); }} className="rounded-design border border-white/70 px-3 py-1.5 text-sm transition hover:bg-white hover:text-ink-900">
                Sign out
              </button>
            </div>
          )}
        </div>
        <button className="ml-auto rounded-md p-2 xl:hidden" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
      </div>
      {open && (
        <div className="border-t border-white/10 px-4 py-3 xl:hidden">
          {nav(true)}
          <div className="mt-2 border-t border-white/10 pt-2">
            {!user ? (
              <>
                <Link href="/login" onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm">Sign in</Link>
                <Link href="/register" onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm">Create account</Link>
              </>
            ) : (
              <button onClick={() => { logout(); setOpen(false); router.push("/"); }} className="block w-full rounded-md px-3 py-2 text-left text-sm">
                Sign out ({user.name})
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
