import { createReadStream, existsSync, readFileSync, statSync } from "node:fs";
import { createInterface } from "node:readline";
import { join } from "node:path";
import pg from "pg";

const { Pool } = pg;
export const pool = new Pool({
  connectionString: process.env.DATABASE_URL ?? "postgresql://medintel:medintel@localhost:5432/medintel",
  connectionTimeoutMillis: 700,
});

export async function query<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {
  try {
    const result = await Promise.race([
      pool.query(sql, params),
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error("Database query timed out.")), 1200)),
    ]);
    return result.rows as T[];
  } catch {
    return [];
  }
}

export function lakePath(...parts: string[]) {
  return join(process.cwd(), "..", "data", "lake", ...parts);
}

export function readJsonl(path: string): any[] {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

const lineCountCache = new Map<string, { mtimeMs: number; count: number }>();
const fieldCountCache = new Map<string, { mtimeMs: number; counts: Record<string, number> }>();

export async function countJsonl(path: string): Promise<number> {
  if (!existsSync(path)) return 0;
  const stat = statSync(path);
  const cached = lineCountCache.get(path);
  if (cached?.mtimeMs === stat.mtimeMs) return cached.count;
  let count = 0;
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  for await (const line of rl) {
    if (line.trim()) count += 1;
  }
  lineCountCache.set(path, { mtimeMs: stat.mtimeMs, count });
  return count;
}

export async function countJsonlByField(path: string, field: string): Promise<Record<string, number>> {
  if (!existsSync(path)) return {};
  const stat = statSync(path);
  const cacheKey = `${path}:${field}`;
  const cached = fieldCountCache.get(cacheKey);
  if (cached?.mtimeMs === stat.mtimeMs) return cached.counts;
  const counts: Record<string, number> = {};
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line.trim()) continue;
    try {
      const value = String(JSON.parse(line)[field] ?? "unknown");
      counts[value] = (counts[value] ?? 0) + 1;
    } catch {
      counts.unknown = (counts.unknown ?? 0) + 1;
    }
  }
  fieldCountCache.set(cacheKey, { mtimeMs: stat.mtimeMs, counts });
  return counts;
}

export function readJson(path: string): any | null {
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf8"));
}

export function activeRunId() {
  if (process.env.MEDINTEL_RUN_ID) return process.env.MEDINTEL_RUN_ID;
  if (existsSync(lakePath("retrieval", "corpus", "local-representative.jsonl"))) return "local-representative";
  if (existsSync(lakePath("retrieval", "corpus", "local-real-small.jsonl"))) return "local-real-small";
  return "local-real-small";
}

export const disclaimer =
  "This is for informational and research support only. It is not medical advice, diagnosis, treatment guidance, or a substitute for clinician judgment.";
