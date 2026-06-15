import { Router } from "express";
import { activeRunId, lakePath, query, readJsonl } from "../db.js";

export const runs = Router();

runs.get("/", async (_req, res) => {
  const rows = await query("SELECT * FROM pipeline_runs ORDER BY updated_at DESC LIMIT 20");
  if (rows.length) return res.json(rows);
  const runId = activeRunId();
  const manifest = readJsonl(lakePath("retrieval", "index_manifests", `${runId}.jsonl`))[0];
  res.json([
    {
      run_id: runId,
      status: manifest ? "completed" : "not_started",
      current_stage: manifest ? "completed" : "real-data pipeline pending",
      documents_read: readJsonl(lakePath("silver", "normalized_documents", `${runId}.jsonl`)).length,
      chunks_indexed: manifest?.indexed_chunks ?? 0,
    },
  ]);
});

runs.get("/:runId", async (req, res) => {
  const rows = await query("SELECT * FROM pipeline_runs WHERE run_id = $1", [req.params.runId]);
  res.json(rows[0] ?? { run_id: req.params.runId, status: "unknown" });
});

runs.get("/:runId/events", async (req, res) => {
  const rows = await query("SELECT * FROM pipeline_events WHERE run_id = $1 ORDER BY created_at DESC LIMIT 100", [req.params.runId]);
  res.json(rows);
});
