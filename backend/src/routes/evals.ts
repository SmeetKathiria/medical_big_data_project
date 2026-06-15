import { Router } from "express";
import { existsSync } from "node:fs";
import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";
import { lakePath, readJson } from "../db.js";

export const evals = Router();

type EvalResult = {
  id?: string;
  question?: string;
  passed?: boolean;
  source_recall?: number;
  doc_hit?: boolean;
  answer_term_recall?: number;
  context_term_recall?: number;
  latency_ms?: number;
  expected_sources?: string[];
  expected_doc_ids?: string[];
  citation_doc_ids?: string[];
  citation_sources?: string[];
  answer_provider?: string;
  answer_model?: string;
};

function prefix(id: string | undefined) {
  return id?.split("-")[0] || "unknown";
}

async function readResults(path: string): Promise<EvalResult[]> {
  if (!existsSync(path)) return [];
  const rows: EvalResult[] = [];
  const rl = createInterface({ input: createReadStream(path), crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line.trim()) continue;
    try {
      rows.push(JSON.parse(line));
    } catch {
      // Skip malformed partial lines while a run is still writing.
    }
  }
  return rows;
}

evals.get("/latest", async (req, res) => {
  const runId = String(req.query.run_id ?? "local-representative");
  const evalDir = lakePath("evals", runId);
  const summaryPath = lakePath("evals", runId, "latest_summary.json");
  const resultsPath = lakePath("evals", runId, "latest_results.jsonl");
  const summary = readJson(summaryPath);
  const results = await readResults(resultsPath);
  const failures = results.filter((result) => !result.passed);
  const failure_breakdown = failures.reduce<Record<string, number>>((acc, result) => {
    const key = prefix(result.id);
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
  const passes = results.filter((result) => result.passed);
  const provider_breakdown = results.reduce<Record<string, number>>((acc, result) => {
    const key = [result.answer_provider, result.answer_model].filter(Boolean).join("/") || "unknown";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  res.json({
    run_id: runId,
    summary,
    failure_breakdown,
    provider_breakdown,
    failed_results: failures,
    passed_results: passes,
    result_count: results.length,
    paths: {
      eval_dir: evalDir,
      summary: summaryPath,
      results: resultsPath,
    },
  });
});
