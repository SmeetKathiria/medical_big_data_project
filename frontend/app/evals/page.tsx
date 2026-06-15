import { api } from "../../components/api";
import { EvalDashboard } from "../../components/EvalDashboard";

export default async function Page() {
  const evalData = await api<any>("/api/evals/latest?run_id=local-representative").catch(() => null);
  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">Signal Quality</h1>
        <p className="page-subtitle">Quality controls for citation coverage, source recall, and answer completeness across clinically relevant review checks.</p>
      </div>
      <EvalDashboard evalData={evalData} />
    </div>
  );
}
