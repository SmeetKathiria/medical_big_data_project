import { Activity } from "lucide-react";
import { MetricCard } from "./MetricCard";

export function ProgressDashboard({ runs }: { runs: any[] }) {
  const run = runs[0] ?? {};
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="page-title">MedIntel Overview</h1>
          <p className="page-subtitle">CMS, FDA, and PubMed processing status.</p>
        </div>
        <div className="status-pill h-10">
          <Activity size={16} />
          {(run.current_stage ?? "waiting").toUpperCase()}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="Run status" value={run.status ?? "not_started"} />
        <MetricCard label="Documents read" value={run.documents_read ?? 0} />
        <MetricCard label="Entities" value={run.entities_extracted ?? 0} />
        <MetricCard label="Indexed records" value={run.chunks_indexed ?? 0} />
      </div>
    </section>
  );
}
