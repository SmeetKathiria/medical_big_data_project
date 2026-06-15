import { Router } from "express";
import { activeRunId, lakePath, query, readJsonl } from "../db.js";

export const policies = Router();

policies.get("/diff", async (req, res) => {
  const rows = await query("SELECT * FROM policy_diffs WHERE ($1 = '' OR topic ILIKE $1) ORDER BY created_at DESC LIMIT 10", [
    req.query.topic ? `%${req.query.topic}%` : "",
  ]);
  if (rows.length) return res.json(rows[0]);
  const diffs = readJsonl(lakePath("gold", "policy_diffs", `${activeRunId()}.jsonl`));
  res.json(diffs[0] ?? { summary: "No CMS policy diff has been generated yet.", diff_json: { citations: [] } });
});
