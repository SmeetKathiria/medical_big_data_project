import { Router } from "express";

export const health = Router();
export const healthPayload = { ok: true, service: "medintel-api" };

health.get("/", (_req, res) => {
  res.json(healthPayload);
});
