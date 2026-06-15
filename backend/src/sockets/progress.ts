import type { Server } from "socket.io";
import { dashboardSnapshot } from "../dashboard.js";
import { query } from "../db.js";

export function registerProgressSocket(io: Server) {
  io.on("connection", (socket) => {
    socket.on("subscribe_dashboard", () => {
      const emitSnapshot = async () => {
        socket.emit("dashboard_snapshot", await dashboardSnapshot());
      };
      void emitSnapshot();
      const timer = setInterval(() => void emitSnapshot(), 2000);
      socket.on("disconnect", () => clearInterval(timer));
    });

    socket.on("subscribe_run", (runId: string) => {
      const timer = setInterval(async () => {
        const runs = await query("SELECT * FROM pipeline_runs WHERE run_id = $1", [runId]);
        const events = await query("SELECT * FROM pipeline_events WHERE run_id = $1 ORDER BY created_at DESC LIMIT 10", [runId]);
        socket.emit("run_progress", runs[0] ?? { run_id: runId, status: "unknown" });
        socket.emit("pipeline_event", events);
      }, 2000);
      socket.on("disconnect", () => clearInterval(timer));
    });
  });
}
