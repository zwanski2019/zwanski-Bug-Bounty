"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

/**
 * Registration form — posts to Fastify API.
 */
export default function RegisterPage() {
  const [msg, setMsg] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const res = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: fd.get("email"),
        password: fd.get("password"),
        handle: fd.get("handle"),
        accountType: fd.get("accountType"),
      }),
    });
    const data = (await res.json()) as { data?: { verificationToken?: string }; error?: { message?: string } };
    if (!res.ok) {
      setMsg(data.error?.message ?? "Error");
      return;
    }
    setMsg(`Registered. Dev token: ${data.data?.verificationToken ?? "n/a"}`);
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-bold">Create account</h1>
      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <input name="email" type="email" required placeholder="Email" className="rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2" />
        <input name="password" type="password" required placeholder="Password (10+ chars)" className="rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2" />
        <input name="handle" required placeholder="Handle" className="rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2" />
        <select name="accountType" className="rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2">
          <option value="researcher">Researcher</option>
          <option value="organization">Organization</option>
        </select>
        <button type="submit" className="rounded-lg bg-watchdog-accent py-2 font-semibold text-black">
          Register
        </button>
      </form>
      {msg && <p className="mt-4 text-sm text-slate-400">{msg}</p>}
    </main>
  );
}
