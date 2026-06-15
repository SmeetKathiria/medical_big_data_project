import { api } from "../../../components/api";

export const dynamic = "force-dynamic";

function cleanMessage(message: unknown) {
  return String(message ?? "")
    .replace(/\/Users\/[^\s"']+/g, "workspace path redacted")
    .replace(/\/private\/[^\s"']+/g, "workspace path redacted")
    .replace(/\/var\/folders\/[^\s"']+/g, "workspace path redacted")
    .replace(/data\/lake\/[^\s"']+/g, "lake artifact")
    .replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, "redacted email");
}

function stageLabel(stage: unknown) {
  return String(stage ?? "event")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default async function Page({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const run = await api<any>(`/api/runs/${runId}`).catch(() => ({ run_id: runId }));
  const events = await api<any[]>(`/api/runs/${runId}/events`).catch(() => []);
  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">Pipeline Run</h1>
        <p className="page-subtitle">Operational progress for the selected pipeline run.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="diagnostic-shell">
          <section className="surface-card p-5">
            <div className="eyebrow">Run Status</div>
            <div className="mt-3 metric-value">{stageLabel(run.status ?? "Pending")}</div>
          </section>
        </div>
        <div className="diagnostic-shell">
          <section className="surface-card p-5">
            <div className="eyebrow">Events</div>
            <div className="mt-3 metric-value">{events.length}</div>
          </section>
        </div>
      </div>
      <div className="surface-card overflow-hidden">
        <div className="surface-header">
          <div className="eyebrow">Event Log</div>
        </div>
        {events.map((event) => (
          <div key={event.id} className="border-t border-line/70 p-4 text-sm font-light leading-6">
            <span className="font-semibold text-green">{stageLabel(event.stage)}</span>: {cleanMessage(event.message)}
          </div>
        ))}
        {!events.length && <div className="border-t border-line/70 p-4 text-sm font-light leading-6 text-muted">No events recorded yet.</div>}
      </div>
    </div>
  );
}
