"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/providers";
import { Alert, Button, Card, Field, Input } from "@/components/ui";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "buyer" as "buyer" | "seller" });
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const pwOk = form.password.length >= 8 && /[A-Za-z]/.test(form.password) && /\d/.test(form.password);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pwOk) return;
    setBusy(true);
    setError(null);
    try {
      const u = await register(form.name, form.email, form.password, form.role);
      router.push(u.role === "seller" ? "/seller" : "/properties");
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-16 md:py-24">
      <Card className="p-8">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Create an account</h1>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <Field label="Name" htmlFor="name" required>
            <Input id="name" required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label="Email" htmlFor="email" required>
            <Input id="email" type="email" required autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          <Field label="Password" htmlFor="password" required hint="At least 8 characters with letters and numbers." error={form.password && !pwOk ? "At least 8 characters with letters and numbers." : undefined}>
            <Input id="password" type="password" required autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </Field>
          <fieldset>
            <legend className="mb-1 text-sm font-medium text-slate-700">I want to</legend>
            <div className="grid grid-cols-2 gap-2">
              {(["buyer", "seller"] as const).map((r) => (
                <label key={r} className={`cursor-pointer rounded-lg border p-3 text-sm ${form.role === r ? "border-brand-600 bg-brand-50" : "border-slate-300"}`}>
                  <input type="radio" name="role" value={r} checked={form.role === r} onChange={() => setForm({ ...form, role: r })} className="sr-only" />
                  <span className="font-medium">{r === "buyer" ? "Explore and invest" : "List a property"}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {error && (
            <Alert tone="red">
              {error.message}
              {error.details?.length > 0 && <ul className="mt-1 list-disc pl-4">{error.details.map((d, i) => <li key={i}>{d.field}: {d.issue}</li>)}</ul>}
            </Alert>
          )}
          <Button type="submit" className="w-full" loading={busy} disabled={!pwOk}>Create account</Button>
        </form>
        <p className="mt-4 text-sm text-slate-600">Already registered? <Link href="/login" className="font-medium text-brand-700 hover:underline">Sign in</Link></p>
      </Card>
    </div>
  );
}
