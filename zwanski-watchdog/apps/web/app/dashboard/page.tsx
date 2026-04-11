/**
 * Authenticated dashboard shell — pass Bearer token manually in dev.
 */
export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-2xl font-bold">Researcher dashboard</h1>
      <p className="mt-4 text-slate-400">
        Wire session cookies and findings feed against <code>/findings</code> in the next iteration.
      </p>
    </main>
  );
}
