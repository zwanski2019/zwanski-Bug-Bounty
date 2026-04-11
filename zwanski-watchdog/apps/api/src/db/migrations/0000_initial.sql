CREATE TYPE "role" AS ENUM ('researcher', 'org_admin', 'super_admin');
CREATE TYPE "subscription_tier" AS ENUM ('basic', 'pro', 'enterprise', 'government');
CREATE TYPE "leak_type" AS ENUM (
  'credential',
  'pii',
  'ai_training_data',
  'system_prompt',
  'api_key',
  'private_key',
  'internal_config',
  'mcp_exposure',
  'other'
);
CREATE TYPE "finding_status" AS ENUM (
  'new',
  'triaged',
  'disclosed',
  'resolved',
  'false_positive'
);
CREATE TYPE "disclosure_status" AS ENUM ('pending', 'sent', 'acknowledged', 'resolved');

CREATE TABLE "users" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "email" varchar(320) NOT NULL UNIQUE,
  "password_hash" text NOT NULL,
  "role" "role" DEFAULT 'researcher' NOT NULL,
  "is_verified" boolean DEFAULT false NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "created_at" timestamptz DEFAULT now() NOT NULL,
  "updated_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "researcher_profiles" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL UNIQUE REFERENCES "users"("id") ON DELETE CASCADE,
  "handle" varchar(64) NOT NULL,
  "bio" text,
  "pgp_public_key" text,
  "verified_at" timestamptz,
  "platforms" text[] DEFAULT ARRAY[]::text[] NOT NULL,
  "reputation_score" integer DEFAULT 0 NOT NULL,
  "created_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "organizations" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "name" varchar(256) NOT NULL,
  "domain" varchar(256) NOT NULL,
  "contact_email" varchar(320) NOT NULL,
  "subscription_tier" "subscription_tier" DEFAULT 'basic' NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "created_at" timestamptz DEFAULT now() NOT NULL,
  "updated_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "org_members" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "org_id" uuid NOT NULL REFERENCES "organizations"("id") ON DELETE CASCADE,
  "user_id" uuid NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
  "role" varchar(64) DEFAULT 'member' NOT NULL,
  "joined_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "findings" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "scanner_source" varchar(128) NOT NULL,
  "raw_content_hash" varchar(64) NOT NULL,
  "severity_score" numeric(4, 2) DEFAULT 0 NOT NULL,
  "leak_type" "leak_type" DEFAULT 'other' NOT NULL,
  "affected_entity" varchar(512) NOT NULL,
  "status" "finding_status" DEFAULT 'new' NOT NULL,
  "scanner_url" text,
  "discovered_at" timestamptz DEFAULT now() NOT NULL,
  "updated_at" timestamptz DEFAULT now() NOT NULL,
  "metadata" jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE "disclosures" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "finding_id" uuid NOT NULL REFERENCES "findings"("id") ON DELETE CASCADE,
  "reported_by" uuid NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
  "reported_to_email" varchar(320) NOT NULL,
  "disclosure_method" varchar(64) NOT NULL,
  "ipfs_cid" text,
  "sha256_anchor" varchar(64),
  "signed_receipt_url" text,
  "disclosed_at" timestamptz DEFAULT now() NOT NULL,
  "status" "disclosure_status" DEFAULT 'pending' NOT NULL
);

CREATE TABLE "subscriptions" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "org_id" uuid NOT NULL REFERENCES "organizations"("id") ON DELETE CASCADE,
  "stripe_customer_id" varchar(128),
  "stripe_subscription_id" varchar(128),
  "tier" "subscription_tier" NOT NULL,
  "is_active" boolean DEFAULT true NOT NULL,
  "current_period_end" timestamptz,
  "created_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "api_keys" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "org_id" uuid NOT NULL REFERENCES "organizations"("id") ON DELETE CASCADE,
  "key_hash" varchar(128) NOT NULL,
  "label" varchar(128) NOT NULL,
  "last_used_at" timestamptz,
  "created_at" timestamptz DEFAULT now() NOT NULL,
  "revoked_at" timestamptz
);

CREATE TABLE "audit_logs" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "actor_id" uuid REFERENCES "users"("id") ON DELETE SET NULL,
  "action" varchar(128) NOT NULL,
  "target_type" varchar(64) NOT NULL,
  "target_id" uuid,
  "ip_address" varchar(64),
  "user_agent" text,
  "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "created_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "trust_scores" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "domain" varchar(256) NOT NULL UNIQUE,
  "score" numeric(4, 2) DEFAULT 10.0 NOT NULL,
  "findings_count" integer DEFAULT 0 NOT NULL,
  "resolved_count" integer DEFAULT 0 NOT NULL,
  "last_calculated_at" timestamptz DEFAULT now() NOT NULL
);

CREATE TABLE "email_verifications" (
  "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
  "user_id" uuid NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
  "token_hash" varchar(128) NOT NULL,
  "expires_at" timestamptz NOT NULL,
  "created_at" timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX "idx_findings_status" ON "findings" ("status");
CREATE INDEX "idx_findings_leak_type" ON "findings" ("leak_type");
CREATE INDEX "idx_audit_created" ON "audit_logs" ("created_at");
CREATE INDEX "idx_trust_domain" ON "trust_scores" ("domain");
