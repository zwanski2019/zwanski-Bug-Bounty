import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

export default async function TrustScorePage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const q = (await searchParams).q;
  let results: { id: string; name: string; domain: string }[] = [];
  if (q) {
    const res = await fetch(`${API}/trust-score/search?q=${encodeURIComponent(q)}`, { next: { revalidate: 60 } });
    if (res.ok) {
      const json = (await res.json()) as { data: typeof results };
      results = json.data;
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-2xl font-bold">Trust score search</h1>
      <form className="mt-6 flex gap-2">
        <input name="q" defaultValue={q} placeholder="Company or domain" className="flex-1 rounded-lg border border-slate-700 bg-watchdog-card px-3 py-2" />
        <button className="rounded-lg bg-watchdog-accent px-4 font-semibold text-black">Search</button>
      </form>
      <ul className="mt-8 space-y-4">
        {results.map((o) => (
          <li key={o.id} className="rounded-xl border border-slate-800 bg-watchdog-card p-4">
            <Link href={`/trust-score/${encodeURIComponent(o.domain)}`} className="font-semibold text-watchdog-accent">
              {o.name}
            </Link>
            <p className="text-sm text-slate-500">{o.domain}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
