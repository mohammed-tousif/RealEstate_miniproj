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

  // Personal pages live in the account menu so the main bar stays short.
  const accountLinks = [
    ...(user ? [{ href: "/favorites", label: "Favourites" }] : []),
    ...(user && (user.role === "seller" || user.role === "admin") ? [{ href: "/seller", label: "My listings" }] : []),
    ...(user?.role === "admin" ? [{ href: "/admin", label: "Admin" }] : []),
  ];
  const [menu, setMenu] = useState(false);
  useEffect(() => setMenu(false), [pathname]);
  const signOut = () => { setMenu(false); setOpen(false); logout(); router.push("/"); };

  const nav = (mobile: boolean) =>
    (mobile ? [...LINKS, ...accountLinks] : LINKS).map((l) => {
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
        <nav className="ml-6 hidden items-center gap-1 lg:flex">{nav(false)}</nav>
        <div className="ml-auto hidden items-center gap-3 lg:flex">
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
            <div className="relative">
              <button
                onClick={() => setMenu(!menu)}
                aria-expanded={menu}
                aria-haspopup="menu"
                aria-label={`Account menu for ${user.name}`}
                className="flex items-center gap-2 rounded-full border border-white/30 py-1 pl-1 pr-3 text-sm transition hover:border-white/70"
              >
                <span className="grid h-7 w-7 place-items-center rounded-full bg-white text-xs font-semibold text-ink-900">{user.name.slice(0, 1).toUpperCase()}</span>
                <span className="max-w-[10rem] truncate">{user.name}</span>
                <svg viewBox="0 0 20 20" className="h-4 w-4 opacity-70" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m5 8 5 5 5-5" /></svg>
              </button>
              {menu && (
                <div role="menu" className="absolute right-0 mt-2 w-56 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 text-sm text-ink-800 shadow-lg">
                  <p className="border-b border-slate-100 px-4 py-2.5 text-xs text-ink-500">Signed in as <span className="font-medium capitalize text-ink-800">{user.role}</span></p>
                  {accountLinks.map((l) => (
                    <Link key={l.href} role="menuitem" href={l.href} className="block px-4 py-2 hover:bg-slate-50">{l.label}</Link>
                  ))}
                  <button role="menuitem" onClick={signOut} className="block w-full border-t border-slate-100 px-4 py-2 text-left hover:bg-slate-50">Sign out</button>
                </div>
              )}
            </div>
          )}
        </div>
        <button className="ml-auto rounded-md p-2 lg:hidden" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
      </div>
      {open && (
        <div className="border-t border-white/10 px-4 py-3 lg:hidden">
          {nav(true)}
          <div className="mt-2 border-t border-white/10 pt-2">
            {!user ? (
              <>
                <Link href="/login" onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm">Sign in</Link>
                <Link href="/register" onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm">Create account</Link>
              </>
            ) : (
              <button onClick={signOut} className="block w-full rounded-md px-3 py-2 text-left text-sm">
                Sign out ({user.name})
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
