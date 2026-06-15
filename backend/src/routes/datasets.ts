import { Router } from "express";
import { activeRunId, countJsonlByField, lakePath, query } from "../db.js";

export const datasets = Router();

datasets.get("/", async (_req, res) => {
  const runId = activeRunId();
  const counts = await countJsonlByField(lakePath("silver", "normalized_documents", `${runId}.jsonl`), "source_type");
  if (Object.keys(counts).length) {
    return res.json(["cms", "fda", "pubmed"].map((source_type) => ({
      source_id: `${runId}-${source_type}`,
      source_type,
      name: `${source_type.toUpperCase()} ${runId} corpus`,
      document_count: counts[source_type] ?? 0,
    })));
  }
  const rows = await query("SELECT * FROM healthcare_sources ORDER BY loaded_at DESC");
  if (rows.length) return res.json(rows);
  return res.json(["cms", "fda", "pubmed"].map((source_type) => ({
    source_id: `${runId}-${source_type}`,
    source_type,
    name: `${source_type.toUpperCase()} ${runId} corpus`,
    document_count: counts[source_type] ?? 0,
  })));
});
