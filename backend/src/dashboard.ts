import { existsSync } from "node:fs";
import { countJsonl, countJsonlByField, lakePath, query, readJsonl } from "./db.js";

type SourceMetric = {
  source_type: string;
  processed_documents: number;
};

type RunSummary = {
  run_id: string;
  profile: string;
  status: string;
  current_stage: string;
  processed_documents: number;
  chunks_indexed: number;
  sources: SourceMetric[];
};

function profileFor(runId: string) {
  if (runId === "local-representative") return "local-representative";
  if (runId === "cloud-full") return "cloud-full";
  return "local-small";
}

function knownRunIds() {
  const ids = new Set<string>();
  for (const runId of ["local-representative", "cloud-full", "local-real-small"]) {
    if (
      existsSync(lakePath("manifests", `${runId}.jsonl`)) ||
      existsSync(lakePath("retrieval", "index_manifests", `${runId}.jsonl`)) ||
      existsSync(lakePath("raw", "pubmed", `${runId}_pubmed.jsonl`))
    ) {
      ids.add(runId);
    }
  }
  return [...ids];
}

function sourceMetric(entry: any, processedBySource: Record<string, number>): SourceMetric {
  return {
    source_type: entry.source_type,
    processed_documents: Number(processedBySource[entry.source_type] ?? 0),
  };
}

export async function dashboardSnapshot() {
  const dbRuns = await query<any>("SELECT * FROM pipeline_runs ORDER BY updated_at DESC LIMIT 20");
  const dbRunById = new Map(dbRuns.map((run) => [run.run_id, run]));
  const ids = new Set([...knownRunIds(), ...dbRuns.map((run) => String(run.run_id))]);

  const runs: RunSummary[] = [];
  for (const runId of ids) {
    const manifest = readJsonl(lakePath("manifests", `${runId}.jsonl`));
    const dbRun = dbRunById.get(runId);
    const normalizedPath = lakePath("silver", "normalized_documents", `${runId}.jsonl`);
    const processedBySource = await countJsonlByField(normalizedPath, "source_type");
    const sources = manifest.map((entry) => sourceMetric(entry, processedBySource));
    const processedDocuments = await countJsonl(lakePath("silver", "normalized_documents", `${runId}.jsonl`));
    const normalizedSources = sources;
    const indexManifest = readJsonl(lakePath("retrieval", "index_manifests", `${runId}.jsonl`))[0];
    runs.push({
      run_id: runId,
      profile: profileFor(runId),
      status: dbRun?.status ?? (indexManifest ? "completed" : manifest.length ? "raw_ready" : "not_started"),
      current_stage: dbRun?.current_stage ?? (indexManifest ? "completed" : manifest.length ? "raw data ready" : "waiting"),
      processed_documents: processedDocuments || Number(dbRun?.documents_read ?? 0),
      chunks_indexed: Number(indexManifest?.indexed_chunks ?? dbRun?.chunks_indexed ?? 0),
      sources: normalizedSources,
    });
  }

  runs.sort((a, b) => {
    const rank: Record<string, number> = { "local-representative": 0, "cloud-full": 1, "local-small": 2 };
    return (rank[a.profile] ?? 9) - (rank[b.profile] ?? 9);
  });

  return {
    active_run_id: runs[0]?.run_id ?? "local-real-small",
    runs,
    generated_at: new Date().toISOString(),
  };
}
