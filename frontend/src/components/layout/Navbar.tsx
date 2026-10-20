"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
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
            "rounded-md px-3 py-2 text-sm font-medium",
            active ? "bg-brand-50 text-brand-800" : "text-slate-700 hover:bg-slate-100",
            mobile && "block",
          )}
        >
          {l.label}
          {l.href === "/compare" && ids.length > 0 && (
            <span className="ml-1.5 rounded-full bg-brand-700 px-1.5 py-0.5 text-[10px] font-semibold text-white">{ids.length}</span>
          )}
        </Link>
      );
    });

  return (
    <header className="sticky top-0 z-[1000] border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold text-slate-900">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-700 text-white" aria-hidden="true">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /></svg>
          </span>
          PropWise <span className="text-brand-700">AI</span>
        </Link>
        <nav className="ml-4 hidden items-center gap-1 md:flex">{nav(false)}</nav>
        <div className="ml-auto hidden items-center gap-2 md:flex">
          {ready && !user && (
            <>
              <Link href="/login" className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">Sign in</Link>
              <Link href="/register" className="rounded-lg bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800">Create account</Link>
            </>
          )}
          {user && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-600">
                {user.name} <span className="text-xs text-slate-400">({user.role})</span>
              </span>
              <button onClick={() => { logout(); router.push("/"); }} className="rounded-md px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
                Sign out
              </button>
            </div>
          )}
        </div>
        <button className="ml-auto rounded-md p-2 md:hidden" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
      </div>
      {open && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 md:hidden">
          {nav(true)}
          <div className="mt-2 border-t border-slate-100 pt-2">
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
