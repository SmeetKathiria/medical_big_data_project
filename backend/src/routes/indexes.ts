import { Router } from "express";
import { activeRunId, lakePath, query, readJsonl } from "../db.js";

export const indexes = Router();

indexes.get("/", async (_req, res) => {
  const manifestRows = readJsonl(lakePath("retrieval", "index_manifests", `${activeRunId()}.jsonl`));
  if (manifestRows.length) return res.json(manifestRows);
  const rows = await query("SELECT * FROM qdrant_indexes ORDER BY created_at DESC");
  if (rows.length) return res.json(rows);
  res.json([]);
});

indexes.get("/active", async (_req, res) => {
  const activeManifest = readJsonl(lakePath("retrieval", "index_manifests", `${activeRunId()}.jsonl`))[0];
  if (activeManifest) return res.json(activeManifest);
  const rows = await query("SELECT * FROM qdrant_indexes WHERE status = 'active' ORDER BY activated_at DESC LIMIT 1");
  if (rows.length) return res.json(rows[0]);
  res.json(null);
});

indexes.post("/:indexId/activate", async (req, res) => {
  await query("UPDATE qdrant_indexes SET status = 'inactive'");
  await query("UPDATE qdrant_indexes SET status = 'active', activated_at = now() WHERE index_id = $1", [req.params.indexId]);
  res.json({ ok: true, index_id: req.params.indexId });
});
