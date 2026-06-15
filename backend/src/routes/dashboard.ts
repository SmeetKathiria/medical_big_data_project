import { Router } from "express";
import { dashboardSnapshot } from "../dashboard.js";

export const dashboard = Router();

dashboard.get("/", async (_req, res) => {
  res.json(await dashboardSnapshot());
});
