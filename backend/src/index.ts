import { config } from "dotenv";
import cors from "cors";
import express from "express";
import { createServer } from "node:http";

config({ path: new URL("../../.env", import.meta.url).pathname });
config();
import { Server } from "socket.io";
import { dashboard } from "./routes/dashboard.js";
import { datasets } from "./routes/datasets.js";
import { evals } from "./routes/evals.js";
import { health } from "./routes/health.js";
import { indexes } from "./routes/indexes.js";
import { policies } from "./routes/policies.js";
import { rag } from "./routes/rag.js";
import { runs } from "./routes/runs.js";
import { registerProgressSocket } from "./sockets/progress.js";

export const app = express();
app.use(cors());
app.use(express.json());
app.use("/api/health", health);
app.use("/api/dashboard", dashboard);
app.use("/api/runs", runs);
app.use("/api/datasets", datasets);
app.use("/api/evals", evals);
app.use("/api/policies", policies);
app.use("/api/indexes", indexes);
app.use("/api/rag", rag);

const server = createServer(app);
const io = new Server(server, { cors: { origin: "*" } });
registerProgressSocket(io);

const port = Number(process.env.BACKEND_PORT ?? 4000);
if (process.env.NODE_ENV !== "test") {
  server.listen(port, () => console.log(`MedIntel API listening on :${port}`));
}
