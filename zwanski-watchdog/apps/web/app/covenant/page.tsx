import { readFile } from "node:fs/promises";
import path from "node:path";

export default async function CovenantPage() {
  let text = "";
  try {
    const root = path.join(process.cwd(), "..", "..", "COVENANT.md");
    text = await readFile(root, "utf8");
  } catch {
    text = "COVENANT.md not found in dev — open from repository root.";
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <article className="prose prose-invert max-w-none whitespace-pre-wrap">{text}</article>
    </main>
  );
}
