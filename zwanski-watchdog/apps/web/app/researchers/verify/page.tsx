/**
 * PGP verification request — submits to API once `/researchers/verify` is wired with file upload.
 */
export default function ResearcherVerifyPage() {
  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <h1 className="text-2xl font-bold">Researcher verification</h1>
      <p className="mt-4 text-slate-400">
        Upload your public PGP key and platform links. An administrator will verify your profile. This form POSTs to{" "}
        <code className="text-watchdog-accent">POST /researchers/verify</code> with your Bearer token.
      </p>
      <textarea
        className="mt-6 h-40 w-full rounded-lg border border-slate-700 bg-watchdog-card p-3 font-mono text-sm"
        placeholder="-----BEGIN PGP PUBLIC KEY BLOCK-----"
        readOnly
      />
      <p className="mt-4 text-xs text-slate-500">Wire the client submit in Phase 1.1 (httpOnly session).</p>
    </main>
  );
}
