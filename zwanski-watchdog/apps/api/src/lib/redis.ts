import Redis from "ioredis";

let singleton: Redis | null = null;

/**
 * Shared Redis connection for refresh tokens and rate limits.
 */
export function getRedis(): Redis {
  if (singleton) return singleton;
  const url = process.env.REDIS_URL ?? "redis://localhost:6379";
  singleton = new Redis(url, { maxRetriesPerRequest: 3 });
  return singleton;
}

export const REFRESH_PREFIX = "watchdog:refresh:";
