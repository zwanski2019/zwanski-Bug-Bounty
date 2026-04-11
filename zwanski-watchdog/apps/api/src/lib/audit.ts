import type { FastifyRequest } from "fastify";
import { db } from "../db/client.js";
import { auditLogs } from "../db/schema.js";

/**
 * Persist an audit log row for security-sensitive actions.
 */
export async function writeAuditLog(input: {
  actorId: string | null;
  action: string;
  targetType: string;
  targetId?: string | null;
  req: FastifyRequest;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const ip = input.req.ip;
  const ua = input.req.headers["user-agent"] ?? null;
  await db.insert(auditLogs).values({
    actorId: input.actorId,
    action: input.action,
    targetType: input.targetType,
    targetId: input.targetId ?? null,
    ipAddress: ip,
    userAgent: typeof ua === "string" ? ua : null,
    metadata: input.metadata ?? {},
  });
}
