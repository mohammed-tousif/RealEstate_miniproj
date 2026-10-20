"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/providers";
import type { UserRole } from "@/lib/types";
import { EmptyState, LinkButton, Spinner } from "@/components/ui";

/** UI convenience only. The backend enforces every permission on its own. */
export function RequireRole({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { user, ready } = useAuth();
  const pathname = usePathname();
  if (!ready)
    return <div className="grid place-items-center py-24 text-slate-400"><Spinner /></div>;
  if (!user)
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <EmptyState title="Please sign in" action={<LinkButton href={`/login?next=${encodeURIComponent(pathname)}`}>Sign in</LinkButton>}>
          You need an account to use this page.
        </EmptyState>
      </div>
    );
  if (!roles.includes(user.role))
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <EmptyState title="Not available for your account">This page is for {roles.join(" or ")} accounts.</EmptyState>
      </div>
    );
  return <>{children}</>;
}
