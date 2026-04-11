/**
 * Shared domain types for Zwanski Watchdog (API, web, workers).
 * @packageDocumentation
 */

/** Application role for RBAC */
export type Role = "researcher" | "org_admin" | "super_admin";

/** Subscription tier for organizations */
export type SubscriptionTier = "basic" | "pro" | "enterprise" | "government";

/** Normalized leak taxonomy */
export type LeakType =
  | "credential"
  | "pii"
  | "ai_training_data"
  | "system_prompt"
  | "api_key"
  | "private_key"
  | "internal_config"
  | "mcp_exposure"
  | "other";

/** Lifecycle of a finding in the platform */
export type FindingStatus =
  | "new"
  | "triaged"
  | "disclosed"
  | "resolved"
  | "false_positive";

/** Disclosure workflow status */
export type DisclosureStatus =
  | "pending"
  | "sent"
  | "acknowledged"
  | "resolved";

export interface User {
  id: string;
  email: string;
  passwordHash: string;
  role: Role;
  isVerified: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ResearcherProfile {
  id: string;
  userId: string;
  handle: string;
  bio: string | null;
  pgpPublicKey: string | null;
  verifiedAt: string | null;
  platforms: string[];
  reputationScore: number;
  createdAt: string;
}

export interface Organization {
  id: string;
  name: string;
  domain: string;
  contactEmail: string;
  subscriptionTier: SubscriptionTier;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface OrgMember {
  id: string;
  orgId: string;
  userId: string;
  role: string;
  joinedAt: string;
}

export interface Finding {
  id: string;
  scannerSource: string;
  rawContentHash: string;
  severityScore: string;
  leakType: LeakType;
  affectedEntity: string;
  status: FindingStatus;
  scannerUrl: string | null;
  discoveredAt: string;
  updatedAt: string;
}

export interface Disclosure {
  id: string;
  findingId: string;
  reportedBy: string;
  reportedToEmail: string;
  disclosureMethod: string;
  ipfsCid: string | null;
  sha256Anchor: string | null;
  signedReceiptUrl: string | null;
  disclosedAt: string;
  status: DisclosureStatus;
}

export interface Subscription {
  id: string;
  orgId: string;
  stripeCustomerId: string | null;
  stripeSubscriptionId: string | null;
  tier: SubscriptionTier;
  isActive: boolean;
  currentPeriodEnd: string | null;
  createdAt: string;
}

export interface ApiKey {
  id: string;
  orgId: string;
  keyHash: string;
  label: string;
  lastUsedAt: string | null;
  createdAt: string;
  revokedAt: string | null;
}

export interface AuditLog {
  id: string;
  actorId: string | null;
  action: string;
  targetType: string;
  targetId: string | null;
  ipAddress: string | null;
  userAgent: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface TrustScore {
  id: string;
  domain: string;
  score: string;
  findingsCount: number;
  resolvedCount: number;
  lastCalculatedAt: string;
}

/** Standard paginated list wrapper */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/** Successful API envelope */
export interface APIResponse<T> {
  ok: true;
  data: T;
}

/** Error API envelope */
export interface APIError {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
