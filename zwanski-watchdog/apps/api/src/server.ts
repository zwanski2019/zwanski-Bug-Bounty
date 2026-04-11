import "dotenv/config";
import { randomBytes, createHash } from "node:crypto";
import Fastify, { type FastifyReply, type FastifyRequest } from "fastify";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import jwt from "@fastify/jwt";
import rateLimit from "@fastify/rate-limit";
import swagger from "@fastify/swagger";
import swaggerUi from "@fastify/swagger-ui";
import { compareSync, hashSync } from "bcryptjs";
import { and, desc, eq, ilike, or, sql } from "drizzle-orm";
import { z } from "zod";
import { db } from "./db/client.js";
import {
  disclosures,
  emailVerifications,
  findings,
  organizations,
  researcherProfiles,
  trustScores,
  users,
} from "./db/schema.js";
import { writeAuditLog } from "./lib/audit.js";
import { getRedis, REFRESH_PREFIX } from "./lib/redis.js";

const PORT = Number(process.env.PORT ?? 4000);
const JWT_SECRET = process.env.JWT_SECRET ?? "dev-insecure-change-me";
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET ?? "dev-refresh-change-me";

type Role = "researcher" | "org_admin" | "super_admin";

interface JwtPayload {
  sub: string;
  role: Role;
}

declare module "fastify" {
  interface FastifyInstance {
    authenticate: (req: FastifyRequest, rep: FastifyReply) => Promise<void>;
    requireRoles: (...roles: Role[]) => (req: FastifyRequest, rep: FastifyReply) => Promise<void>;
  }
}

declare module "@fastify/jwt" {
  interface FastifyJWT {
    payload: JwtPayload;
    user: JwtPayload;
  }
}

const app = Fastify({ logger: true, trustProxy: true });

await app.register(helmet, { global: true });
await app.register(cors, { origin: true, credentials: true });
await app.register(jwt, { secret: JWT_SECRET, sign: { expiresIn: "15m" } });
await app.register(rateLimit, {
  global: true,
  max: 100,
  timeWindow: "1 minute",
});
await app.register(swagger, {
  openapi: {
    info: {
      title: "Zwanski Watchdog API",
      description: "Ethical leak detection & disclosure platform",
      version: "0.1.0",
    },
  },
});
await app.register(swaggerUi, { routePrefix: "/docs" });

app.decorate(
  "authenticate",
  async function (req: FastifyRequest, rep: FastifyReply) {
    try {
      await req.jwtVerify();
      req.user = req.user as JwtPayload;
    } catch {
      rep.status(401).send({ ok: false, error: { code: "unauthorized", message: "Invalid token" } });
    }
  },
);

app.decorate("requireRoles", (...roles: Role[]) => {
  return async (req: FastifyRequest, rep: FastifyReply) => {
    await app.authenticate(req, rep);
    if (rep.sent) return;
    const u = req.user as JwtPayload;
    if (!roles.includes(u.role)) {
      rep.status(403).send({ ok: false, error: { code: "forbidden", message: "Insufficient role" } });
    }
  };
});

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(10),
  handle: z.string().min(3).max(64),
  accountType: z.enum(["researcher", "organization"]).default("researcher"),
});

app.post("/auth/register", async (req, rep) => {
  const body = registerSchema.safeParse(req.body);
  if (!body.success) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: body.error.message } });
  }
  const { email, password, handle, accountType } = body.data;
  const exists = await db.select().from(users).where(eq(users.email, email)).limit(1);
  if (exists.length) {
    return rep.status(409).send({ ok: false, error: { code: "exists", message: "Email in use" } });
  }
  const role: Role = accountType === "organization" ? "org_admin" : "researcher";
  const [user] = await db
    .insert(users)
    .values({
      email,
      passwordHash: hashSync(password, 12),
      role,
    })
    .returning();

  if (role === "researcher") {
    await db.insert(researcherProfiles).values({ userId: user.id, handle });
  } else {
    await db.insert(organizations).values({
      name: `${handle} Org`,
      domain: "pending-verification.local",
      contactEmail: email,
      subscriptionTier: "basic",
    });
  }

  const raw = randomBytes(32).toString("hex");
  const tokenHash = createHash("sha256").update(raw, "utf8").digest("hex");
  await db.insert(emailVerifications).values({
    userId: user.id,
    tokenHash,
    expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 24 * 3),
  });

  await writeAuditLog({
    actorId: user.id,
    action: "auth.register",
    targetType: "user",
    targetId: user.id,
    req,
  });

  return rep.send({
    ok: true,
    data: {
      userId: user.id,
      verificationToken: raw,
      message: "Verification email would be sent in production.",
    },
  });
});

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

app.post("/auth/login", async (req, rep) => {
  const body = loginSchema.safeParse(req.body);
  if (!body.success) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: body.error.message } });
  }
  const [user] = await db.select().from(users).where(eq(users.email, body.data.email)).limit(1);
  if (!user || !compareSync(body.data.password, user.passwordHash)) {
    return rep.status(401).send({ ok: false, error: { code: "invalid_credentials", message: "Bad login" } });
  }
  if (!user.isActive) {
    return rep.status(403).send({ ok: false, error: { code: "suspended", message: "Account disabled" } });
  }
  const accessToken = await rep.jwtSign({ sub: user.id, role: user.role as Role });
  const refresh = randomBytes(48).toString("hex");
  await getRedis().set(`${REFRESH_PREFIX}${refresh}`, user.id, "EX", 60 * 60 * 24 * 7);
  await writeAuditLog({ actorId: user.id, action: "auth.login", targetType: "user", targetId: user.id, req });
  return rep.send({ ok: true, data: { accessToken, refreshToken: refresh, expiresIn: 900 } });
});

app.post("/auth/refresh", async (req, rep) => {
  const schema = z.object({ refreshToken: z.string().min(10) });
  const body = schema.safeParse(req.body);
  if (!body.success) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: body.error.message } });
  }
  const userId = await getRedis().get(`${REFRESH_PREFIX}${body.data.refreshToken}`);
  if (!userId) {
    return rep.status(401).send({ ok: false, error: { code: "invalid_refresh", message: "Expired" } });
  }
  const [user] = await db.select().from(users).where(eq(users.id, userId)).limit(1);
  if (!user) {
    return rep.status(401).send({ ok: false, error: { code: "invalid_refresh", message: "User missing" } });
  }
  await getRedis().del(`${REFRESH_PREFIX}${body.data.refreshToken}`);
  const newRefresh = randomBytes(48).toString("hex");
  await getRedis().set(`${REFRESH_PREFIX}${newRefresh}`, user.id, "EX", 60 * 60 * 24 * 7);
  const accessToken = await rep.jwtSign({ sub: user.id, role: user.role as Role });
  return rep.send({ ok: true, data: { accessToken, refreshToken: newRefresh, expiresIn: 900 } });
});

app.post("/auth/logout", async (req, rep) => {
  const schema = z.object({ refreshToken: z.string().optional() });
  const body = schema.safeParse(req.body);
  if (body.success && body.data.refreshToken) {
    await getRedis().del(`${REFRESH_PREFIX}${body.data.refreshToken}`);
  }
  return rep.send({ ok: true, data: { loggedOut: true } });
});

app.post<{ Params: { token: string } }>("/auth/verify-email/:token", async (req, rep) => {
  const tokenHash = createHash("sha256").update(req.params.token, "utf8").digest("hex");
  const [row] = await db
    .select()
    .from(emailVerifications)
    .where(eq(emailVerifications.tokenHash, tokenHash))
    .limit(1);
  if (!row || row.expiresAt < new Date()) {
    return rep.status(400).send({ ok: false, error: { code: "invalid_token", message: "Bad or expired" } });
  }
  await db.update(users).set({ isVerified: true, updatedAt: new Date() }).where(eq(users.id, row.userId));
  await db.delete(emailVerifications).where(eq(emailVerifications.id, row.id));
  await writeAuditLog({ actorId: row.userId, action: "auth.verify_email", targetType: "user", targetId: row.userId, req });
  return rep.send({ ok: true, data: { verified: true } });
});

app.post("/auth/forgot-password", async (_req, rep) => {
  return rep.status(202).send({ ok: true, data: { message: "If the email exists, a reset link will be sent." } });
});

app.post<{ Params: { token: string } }>("/auth/reset-password/:token", async (_req, rep) => {
  return rep.status(501).send({ ok: false, error: { code: "not_implemented", message: "Wire email provider first" } });
});

app.get("/researchers/me", { preHandler: app.requireRoles("researcher", "super_admin") }, async (req, rep) => {
  const uid = (req.user as JwtPayload).sub;
  const [profile] = await db.select().from(researcherProfiles).where(eq(researcherProfiles.userId, uid)).limit(1);
  if (!profile) {
    return rep.status(404).send({ ok: false, error: { code: "no_profile", message: "Create profile via register" } });
  }
  return rep.send({ ok: true, data: profile });
});

const profileUpdate = z.object({
  handle: z.string().min(3).max(64).optional(),
  bio: z.string().max(2000).optional().nullable(),
  pgpPublicKey: z.string().max(100_000).optional().nullable(),
  platforms: z.array(z.string()).optional(),
});

app.put("/researchers/me", { preHandler: app.requireRoles("researcher", "super_admin") }, async (req, rep) => {
  const uid = (req.user as JwtPayload).sub;
  const body = profileUpdate.safeParse(req.body);
  if (!body.success) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: body.error.message } });
  }
  const patch: Record<string, unknown> = {};
  if (body.data.handle !== undefined) patch.handle = body.data.handle;
  if (body.data.bio !== undefined) patch.bio = body.data.bio;
  if (body.data.pgpPublicKey !== undefined) patch.pgpPublicKey = body.data.pgpPublicKey;
  if (body.data.platforms !== undefined) patch.platforms = body.data.platforms;
  if (Object.keys(patch).length === 0) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: "No fields" } });
  }
  await db.update(researcherProfiles).set(patch).where(eq(researcherProfiles.userId, uid));
  await writeAuditLog({ actorId: uid, action: "researcher.profile_update", targetType: "researcher", targetId: uid, req });
  return rep.send({ ok: true, data: { updated: true } });
});

app.post("/researchers/verify", { preHandler: app.requireRoles("researcher", "super_admin") }, async (req, rep) => {
  await writeAuditLog({
    actorId: (req.user as JwtPayload).sub,
    action: "researcher.verify_request",
    targetType: "researcher",
    targetId: (req.user as JwtPayload).sub,
    req,
  });
  return rep.send({ ok: true, data: { message: "Queued for admin review" } });
});

app.get("/researchers/leaderboard", async (_req, rep) => {
  const rows = await db
    .select()
    .from(researcherProfiles)
    .orderBy(desc(researcherProfiles.reputationScore))
    .limit(50);
  return rep.send({ ok: true, data: rows });
});

const findingStatusSchema = z.enum(["new", "triaged", "disclosed", "resolved", "false_positive"]).optional();
const leakTypeFilterSchema = z
  .enum([
    "credential",
    "pii",
    "ai_training_data",
    "system_prompt",
    "api_key",
    "private_key",
    "internal_config",
    "mcp_exposure",
    "other",
  ])
  .optional();

const listQuery = z.object({
  page: z.coerce.number().min(1).default(1),
  pageSize: z.coerce.number().min(1).max(100).default(20),
  status: findingStatusSchema,
  leakType: leakTypeFilterSchema,
});

app.get("/findings", { preHandler: app.requireRoles("researcher", "org_admin", "super_admin") }, async (req, rep) => {
  const q = listQuery.safeParse(req.query);
  if (!q.success) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: q.error.message } });
  }
  const { page, pageSize, status, leakType } = q.data;
  const conditions = [];
  if (status) conditions.push(eq(findings.status, status));
  if (leakType) conditions.push(eq(findings.leakType, leakType));
  const whereClause = conditions.length ? and(...conditions) : undefined;

  const base = db.select().from(findings);
  const rows = whereClause
    ? await base
        .where(whereClause)
        .orderBy(desc(findings.discoveredAt))
        .limit(pageSize)
        .offset((page - 1) * pageSize)
    : await base.orderBy(desc(findings.discoveredAt)).limit(pageSize).offset((page - 1) * pageSize);

  const countBase = db.select({ count: sql<number>`count(*)::int` }).from(findings);
  const [{ count }] = whereClause
    ? await countBase.where(whereClause)
    : await countBase;
  return rep.send({
    ok: true,
    data: { items: rows, page, pageSize, total: count, hasMore: page * pageSize < count },
  });
});

app.get<{ Params: { id: string } }>("/findings/:id", { preHandler: app.authenticate }, async (req, rep) => {
  const [row] = await db.select().from(findings).where(eq(findings.id, req.params.id)).limit(1);
  if (!row) return rep.status(404).send({ ok: false, error: { code: "not_found", message: "Finding" } });
  return rep.send({ ok: true, data: row });
});

app.post<{ Params: { id: string } }>(
  "/findings/:id/disclose",
  { preHandler: app.requireRoles("researcher", "super_admin") },
  async (req, rep) => {
    const schema = z.object({ email: z.string().email(), method: z.string().default("email") });
    const body = schema.safeParse(req.body);
    if (!body.success) {
      return rep.status(400).send({ ok: false, error: { code: "validation", message: body.error.message } });
    }
    const uid = (req.user as JwtPayload).sub;
    const [f] = await db.select().from(findings).where(eq(findings.id, req.params.id)).limit(1);
    if (!f) return rep.status(404).send({ ok: false, error: { code: "not_found", message: "Finding" } });
    const [d] = await db
      .insert(disclosures)
      .values({
        findingId: f.id,
        reportedBy: uid,
        reportedToEmail: body.data.email,
        disclosureMethod: body.data.method,
        status: "pending",
      })
      .returning();
    await db.update(findings).set({ status: "disclosed", updatedAt: new Date() }).where(eq(findings.id, f.id));
    await writeAuditLog({
      actorId: uid,
      action: "finding.disclose",
      targetType: "finding",
      targetId: f.id,
      req,
      metadata: { disclosureId: d.id },
    });
    return rep.send({ ok: true, data: d });
  },
);

app.post<{ Params: { id: string } }>(
  "/findings/:id/false-positive",
  { preHandler: app.requireRoles("researcher", "super_admin") },
  async (req, rep) => {
    const uid = (req.user as JwtPayload).sub;
    const [f] = await db.select().from(findings).where(eq(findings.id, req.params.id)).limit(1);
    if (!f) return rep.status(404).send({ ok: false, error: { code: "not_found", message: "Finding" } });
    await db.update(findings).set({ status: "false_positive", updatedAt: new Date() }).where(eq(findings.id, f.id));
    await writeAuditLog({ actorId: uid, action: "finding.false_positive", targetType: "finding", targetId: f.id, req });
    return rep.send({ ok: true, data: { updated: true } });
  },
);

app.get("/findings/stats", { preHandler: app.authenticate }, async (_req, rep) => {
  const byType = await db
    .select({ leakType: findings.leakType, c: sql<number>`count(*)::int` })
    .from(findings)
    .groupBy(findings.leakType);
  const byStatus = await db
    .select({ status: findings.status, c: sql<number>`count(*)::int` })
    .from(findings)
    .groupBy(findings.status);
  return rep.send({ ok: true, data: { byType, byStatus } });
});

app.get("/disclosures", { preHandler: app.authenticate }, async (req, rep) => {
  const uid = (req.user as JwtPayload).sub;
  const rows = await db.select().from(disclosures).where(eq(disclosures.reportedBy, uid)).orderBy(desc(disclosures.disclosedAt));
  return rep.send({ ok: true, data: rows });
});

app.get<{ Params: { id: string } }>("/disclosures/:id", { preHandler: app.authenticate }, async (req, rep) => {
  const uid = (req.user as JwtPayload).sub;
  const [row] = await db
    .select()
    .from(disclosures)
    .where(and(eq(disclosures.id, req.params.id), eq(disclosures.reportedBy, uid)))
    .limit(1);
  if (!row) return rep.status(404).send({ ok: false, error: { code: "not_found", message: "Disclosure" } });
  return rep.send({ ok: true, data: row });
});

app.get<{ Params: { id: string } }>("/disclosures/:id/receipt", { preHandler: app.authenticate }, async (req, rep) => {
  return rep.status(501).send({ ok: false, error: { code: "not_implemented", message: "PDF streaming next sprint" } });
});

app.get<{ Params: { domain: string } }>("/trust-score/:domain", async (req, rep) => {
  const [row] = await db
    .select()
    .from(trustScores)
    .where(eq(trustScores.domain, req.params.domain.toLowerCase()))
    .limit(1);
  if (!row) {
    return rep.status(404).send({ ok: false, error: { code: "not_found", message: "Domain" } });
  }
  return rep.send({ ok: true, data: row });
});

app.get("/trust-score/search", async (req, rep) => {
  const q = z.object({ q: z.string().min(1) }).safeParse(req.query);
  if (!q.success) {
    return rep.status(400).send({ ok: false, error: { code: "validation", message: "q required" } });
  }
  const term = `%${q.data.q}%`;
  const orgs = await db
    .select()
    .from(organizations)
    .where(or(ilike(organizations.name, term), ilike(organizations.domain, term)))
    .limit(20);
  return rep.send({ ok: true, data: orgs });
});

app.get("/org/me", { preHandler: app.requireRoles("org_admin", "super_admin") }, async (_req, rep) => {
  return rep.send({ ok: true, data: { message: "Link org_members in Phase 1.1" } });
});

app.get("/admin/stats", { preHandler: app.requireRoles("super_admin") }, async (_req, rep) => {
  const [{ users: uc }] = await db.select({ users: sql<number>`count(*)::int` }).from(users);
  const [{ fc }] = await db.select({ fc: sql<number>`count(*)::int` }).from(findings);
  return rep.send({ ok: true, data: { users: uc, findings: fc } });
});

app.post("/webhooks/stripe", async (req, rep) => {
  app.log.info({ body: req.body }, "stripe webhook stub");
  return rep.send({ received: true });
});

app.get("/public/stats", async (_req, rep) => {
  const [{ fc }] = await db.select({ fc: sql<number>`count(*)::int` }).from(findings);
  const [{ rc }] = await db.select({ rc: sql<number>`count(*)::int` }).from(researcherProfiles);
  return rep.send({ ok: true, data: { findings: fc, researchersActive: rc } });
});

app.get("/health", async () => ({ ok: true, service: "zwanski-watchdog-api" }));

const start = async () => {
  try {
    await app.listen({ port: PORT, host: "0.0.0.0" });
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();
