const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

async function fetchStats() {
  try {
    const res = await fetch(`${API}/public/stats`, { next: { revalidate: 30 } });
    if (!res.ok) return null;
    const json = (await res.json()) as { data?: { findings?: number; researchersActive?: number } };
    return json.data ?? null;
  } catch {
    return null;
  }
}

/**
 * Marketing landing — connects to live API stats when available.
 */
export default async function HomePage() {
  const stats = await fetchStats();

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-16 px-6 py-16">
      <header className="space-y-6 text-center">
        <p className="text-sm uppercase tracking-[0.3em] text-watchdog-accent">Zwanski Tech</p>
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">The Internet&apos;s Ethical Watchdog</h1>
        <p className="mx-auto max-w-2xl text-slate-400">
          Scan → classify → disclose. Open-source core for responsible leak discovery aligned with{" "}
          <a href="/covenant" className="text-watchdog-accent underline">
            our covenant
          </a>
          .
        </p>
        <div className="flex flex-wrap justify-center gap-8 text-left">
          <Stat label="Findings (seed)" value={stats?.findings ?? "—"} />
          <Stat label="Researchers (profiles)" value={stats?.researchersActive ?? "—"} />
        </div>
      </header>

      <section className="grid gap-8 md:grid-cols-3">
        {[
          { t: "1. Scan", d: "Passive modules discover public exposures only." },
          { t: "2. Classify", d: "AI + rules score severity without exfiltrating secrets." },
          { t: "3. Disclose", d: "72h private notice workflow with signed receipts." },
        ].map((s) => (
          <article key={s.t} className="rounded-2xl border border-slate-800 bg-watchdog-card p-6">
            <h2 className="text-lg font-semibold text-watchdog-accent">{s.t}</h2>
            <p className="mt-2 text-sm text-slate-400">{s.d}</p>
          </article>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-watchdog-card p-8">
        <h2 className="text-xl font-semibold">Trust score</h2>
        <p className="mt-2 text-sm text-slate-400">Search public accountability scores by domain.</p>
        <form action="/trust-score" className="mt-4 flex gap-2">
          <input
            name="q"
            placeholder="example.com"
            className="flex-1 rounded-lg border border-slate-700 bg-watchdog-bg px-4 py-2 text-sm"
          />
          <button type="submit" className="rounded-lg bg-watchdog-accent px-4 py-2 text-sm font-semibold text-black">
            Search
          </button>
        </form>
      </section>

      <footer className="border-t border-slate-800 pt-8 text-center text-xs text-slate-500">
        MIT License · Mohamed Ibrahim (zwanski) / Zwanski Tech ·{" "}
        <a href="https://github.com/zwanski2019" className="underline">
          GitHub
        </a>
      </footer>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-watchdog-bg px-6 py-4">
      <p className="text-2xl font-bold text-watchdog-accent">{value}</p>
      <p className="text-xs uppercase tracking-wider text-slate-500">{label}</p>
    </div>
  );
}
