const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

export default async function TrustScoreDetailPage({ params }: { params: Promise<{ domain: string }> }) {
  const domain = (await params).domain;
  const res = await fetch(`${API}/trust-score/${encodeURIComponent(domain)}`, { next: { revalidate: 60 } });
  if (!res.ok) {
    return (
      <main className="px-6 py-16">
        <p>Domain not indexed yet.</p>
      </main>
    );
  }
  const json = (await res.json()) as {
    data: { score: string; findingsCount: number; resolvedCount: number; domain: string };
  };

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <h1 className="text-3xl font-bold">{json.data.domain}</h1>
      <p className="mt-6 text-5xl font-black text-watchdog-accent">{json.data.score}</p>
      <p className="text-sm text-slate-500">Trust score (0–10)</p>
      <dl className="mt-8 grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-slate-500">Findings</dt>
          <dd className="text-xl font-semibold">{json.data.findingsCount}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Resolved</dt>
          <dd className="text-xl font-semibold">{json.data.resolvedCount}</dd>
        </div>
      </dl>
    </main>
  );
}
