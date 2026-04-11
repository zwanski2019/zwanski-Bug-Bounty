import "dotenv/config";
import { hashSync } from "bcryptjs";
import { eq } from "drizzle-orm";
import { db, pgClient } from "./client.js";
import {
  findings,
  organizations,
  researcherProfiles,
  trustScores,
  users,
} from "./schema.js";

async function main() {
  const email = "researcher@example.com";
  const existing = await db.select().from(users).where(eq(users.email, email)).limit(1);
  if (existing.length > 0) {
    console.log("Seed skipped: user exists");
    await pgClient.end();
    return;
  }

  const [u] = await db
    .insert(users)
    .values({
      email,
      passwordHash: hashSync("ChangeMe!23", 12),
      role: "researcher",
      isVerified: true,
    })
    .returning();

  await db.insert(researcherProfiles).values({
    userId: u.id,
    handle: "demo_researcher",
    bio: "Seed profile",
    reputationScore: 10,
  });

  const [admin] = await db
    .insert(users)
    .values({
      email: "admin@example.com",
      passwordHash: hashSync("AdminChangeMe!23", 12),
      role: "super_admin",
      isVerified: true,
    })
    .returning();

  await db.insert(researcherProfiles).values({
    userId: admin.id,
    handle: "watchdog_admin",
    bio: "Super admin seed",
    reputationScore: 0,
  });

  const [org] = await db
    .insert(organizations)
    .values({
      name: "Example Corp",
      domain: "example.com",
      contactEmail: "security@example.com",
      subscriptionTier: "basic",
    })
    .returning();

  await db.insert(trustScores).values({
    domain: "example.com",
    score: "8.50",
    findingsCount: 2,
    resolvedCount: 1,
  });

  await db.insert(findings).values({
    scannerSource: "seed",
    rawContentHash: "a".repeat(64),
    severityScore: "6.50",
    leakType: "api_key",
    affectedEntity: "example.com",
    status: "new",
    scannerUrl: "https://example.com",
  });

  console.log("Seed OK:", { researcher: u.email, admin: admin.email, org: org.domain });
  await pgClient.end();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
