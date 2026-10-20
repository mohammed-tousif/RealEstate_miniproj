"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import type { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/providers";
import { Alert, Button, Card, Field, Input } from "@/components/ui";

function LoginInner() {
  const { login } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next") || "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await login(email, password);
      router.push(next !== "/" ? next : u.role === "admin" ? "/admin" : u.role === "seller" ? "/seller" : "/properties");
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <Card className="p-6">
        <h1 className="text-xl font-semibold">Sign in</h1>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="Email" htmlFor="email" required>
            <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Password" htmlFor="password" required>
            <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          {error && <Alert tone="red">{error}</Alert>}
          <Button type="submit" className="w-full" loading={busy}>Sign in</Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          New here? <Link href="/register" className="font-medium text-brand-700 hover:underline">Create an account</Link>
        </p>
        <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
          Demo accounts from the seed script: admin@, seller1@ or buyer@demo.propwise.example (password from
          SEED_DEMO_PASSWORD).
        </p>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return <Suspense fallback={null}><LoginInner /></Suspense>;
}
