import { api } from "../components/api";
import { DashboardLive } from "../components/DashboardLive";

export default async function Page() {
  const snapshot = await api<any>("/api/dashboard").catch(() => ({ active_run_id: "local-real-small", runs: [], generated_at: new Date().toISOString() }));
  const evalData = await api<any>("/api/evals/latest?run_id=local-representative").catch(() => null);
  return <DashboardLive initialSnapshot={snapshot} initialEvalData={evalData} />;
}
