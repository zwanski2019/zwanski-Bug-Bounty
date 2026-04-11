import { sql } from "drizzle-orm";
import {
  boolean,
  decimal,
  integer,
  jsonb,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uuid,
  varchar,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

export const roleEnum = pgEnum("role", ["researcher", "org_admin", "super_admin"]);
export const subscriptionTierEnum = pgEnum("subscription_tier", [
  "basic",
  "pro",
  "enterprise",
  "government",
]);
export const leakTypeEnum = pgEnum("leak_type", [
  "credential",
  "pii",
  "ai_training_data",
  "system_prompt",
  "api_key",
  "private_key",
  "internal_config",
  "mcp_exposure",
  "other",
]);
export const findingStatusEnum = pgEnum("finding_status", [
  "new",
  "triaged",
  "disclosed",
  "resolved",
  "false_positive",
]);
export const disclosureStatusEnum = pgEnum("disclosure_status", [
  "pending",
  "sent",
  "acknowledged",
  "resolved",
]);

export const users = pgTable("users", {
  id: uuid("id").defaultRandom().primaryKey(),
  email: varchar("email", { length: 320 }).notNull().unique(),
  passwordHash: text("password_hash").notNull(),
  role: roleEnum("role").notNull().default("researcher"),
  isVerified: boolean("is_verified").notNull().default(false),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const researcherProfiles = pgTable("researcher_profiles", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: uuid("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" })
    .unique(),
  handle: varchar("handle", { length: 64 }).notNull(),
  bio: text("bio"),
  pgpPublicKey: text("pgp_public_key"),
  verifiedAt: timestamp("verified_at", { withTimezone: true }),
  platforms: text("platforms").array().notNull().default(sql`ARRAY[]::text[]`),
  reputationScore: integer("reputation_score").notNull().default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const organizations = pgTable("organizations", {
  id: uuid("id").defaultRandom().primaryKey(),
  name: varchar("name", { length: 256 }).notNull(),
  domain: varchar("domain", { length: 256 }).notNull(),
  contactEmail: varchar("contact_email", { length: 320 }).notNull(),
  subscriptionTier: subscriptionTierEnum("subscription_tier").notNull().default("basic"),
  isActive: boolean("is_active").notNull().default(true),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const orgMembers = pgTable("org_members", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id")
    .notNull()
    .references(() => organizations.id, { onDelete: "cascade" }),
  userId: uuid("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  role: varchar("role", { length: 64 }).notNull().default("member"),
  joinedAt: timestamp("joined_at", { withTimezone: true }).notNull().defaultNow(),
});

export const findings = pgTable("findings", {
  id: uuid("id").defaultRandom().primaryKey(),
  scannerSource: varchar("scanner_source", { length: 128 }).notNull(),
  rawContentHash: varchar("raw_content_hash", { length: 64 }).notNull(),
  severityScore: decimal("severity_score", { precision: 4, scale: 2 }).notNull().default("0"),
  leakType: leakTypeEnum("leak_type").notNull().default("other"),
  affectedEntity: varchar("affected_entity", { length: 512 }).notNull(),
  status: findingStatusEnum("status").notNull().default("new"),
  scannerUrl: text("scanner_url"),
  discoveredAt: timestamp("discovered_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  metadata: jsonb("metadata").$type<Record<string, unknown>>().default({}),
});

export const disclosures = pgTable("disclosures", {
  id: uuid("id").defaultRandom().primaryKey(),
  findingId: uuid("finding_id")
    .notNull()
    .references(() => findings.id, { onDelete: "cascade" }),
  reportedBy: uuid("reported_by")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  reportedToEmail: varchar("reported_to_email", { length: 320 }).notNull(),
  disclosureMethod: varchar("disclosure_method", { length: 64 }).notNull(),
  ipfsCid: text("ipfs_cid"),
  sha256Anchor: varchar("sha256_anchor", { length: 64 }),
  signedReceiptUrl: text("signed_receipt_url"),
  disclosedAt: timestamp("disclosed_at", { withTimezone: true }).notNull().defaultNow(),
  status: disclosureStatusEnum("status").notNull().default("pending"),
});

export const subscriptions = pgTable("subscriptions", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id")
    .notNull()
    .references(() => organizations.id, { onDelete: "cascade" }),
  stripeCustomerId: varchar("stripe_customer_id", { length: 128 }),
  stripeSubscriptionId: varchar("stripe_subscription_id", { length: 128 }),
  tier: subscriptionTierEnum("tier").notNull(),
  isActive: boolean("is_active").notNull().default(true),
  currentPeriodEnd: timestamp("current_period_end", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const apiKeys = pgTable("api_keys", {
  id: uuid("id").defaultRandom().primaryKey(),
  orgId: uuid("org_id")
    .notNull()
    .references(() => organizations.id, { onDelete: "cascade" }),
  keyHash: varchar("key_hash", { length: 128 }).notNull(),
  label: varchar("label", { length: 128 }).notNull(),
  lastUsedAt: timestamp("last_used_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
});

export const auditLogs = pgTable("audit_logs", {
  id: uuid("id").defaultRandom().primaryKey(),
  actorId: uuid("actor_id").references(() => users.id, { onDelete: "set null" }),
  action: varchar("action", { length: 128 }).notNull(),
  targetType: varchar("target_type", { length: 64 }).notNull(),
  targetId: uuid("target_id"),
  ipAddress: varchar("ip_address", { length: 64 }),
  userAgent: text("user_agent"),
  metadata: jsonb("metadata").$type<Record<string, unknown>>().notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const trustScores = pgTable("trust_scores", {
  id: uuid("id").defaultRandom().primaryKey(),
  domain: varchar("domain", { length: 256 }).notNull().unique(),
  score: decimal("score", { precision: 4, scale: 2 }).notNull().default("10.0"),
  findingsCount: integer("findings_count").notNull().default(0),
  resolvedCount: integer("resolved_count").notNull().default(0),
  lastCalculatedAt: timestamp("last_calculated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const emailVerifications = pgTable("email_verifications", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: uuid("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  tokenHash: varchar("token_hash", { length: 128 }).notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const usersRelations = relations(users, ({ one, many }) => ({
  profile: one(researcherProfiles, {
    fields: [users.id],
    references: [researcherProfiles.userId],
  }),
  disclosures: many(disclosures),
}));

export const findingsRelations = relations(findings, ({ many }) => ({
  disclosures: many(disclosures),
}));
