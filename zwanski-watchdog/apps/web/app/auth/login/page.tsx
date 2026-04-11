"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

/**
 * Login — stores JWT in memory (httpOnly cookie wiring in Phase 1.1).
 */
export default function LoginPage() {
  const [token, setToken] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: fd.get("email"), password: fd.get("password") }),
    });
    const data = (await res.json()) as { data?: { accessToken?: string } };
    if (res.ok && data.data?.accessToken) setToken(data.data.accessToken);
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-bold">Sign in</h1>
      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <input name="email" type="email" required className="rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2" />
        <input name="password" type="password" required className="rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2" />
        <button type="submit" className="rounded-lg bg-watchdog-accent py-2 font-semibold text-black">
          Login
        </button>
      </form>
      {token && (
        <p className="mt-4 break-all text-xs text-slate-500">
          Access token (dev only): <code>{token}</code>
        </p>
      )}
    </main>
  );
}
