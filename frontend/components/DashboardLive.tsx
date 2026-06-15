"use client";

import { useEffect, useMemo, useState } from "react";
import { io, type Socket } from "socket.io-client";
import { API_URL, api } from "./api";
import { MetricCard } from "./MetricCard";

type SourceMetric = {
  source_type: string;
  processed_documents: number;
};

type RunSummary = {
  run_id: string;
  profile: string;
  status: string;
  current_stage: string;
  processed_documents: number;
  chunks_indexed: number;
  sources: SourceMetric[];
};

type DashboardSnapshot = {
  active_run_id: string;
  runs: RunSummary[];
  generated_at: string;
};

type EvalSnapshot = {
  summary?: {
    pass_rate?: number;
    doc_hit_rate?: number;
    avg_source_recall?: number;
  };
};

function socketUrl() {
  return API_URL.replace(/^http/, "ws");
}

function formatNumber(value: number | undefined) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function formatPercent(value: number | undefined) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "-";
}

function sourceLabel(source: string | undefined) {
  if (source === "pubmed") return "PubMed";
  return source?.toUpperCase() ?? "-";
}

export function DashboardLive({ initialSnapshot, initialEvalData }: { initialSnapshot: DashboardSnapshot; initialEvalData?: EvalSnapshot | null }) {
  const [snapshot, setSnapshot] = useState(initialSnapshot);
  const [evalData, setEvalData] = useState<EvalSnapshot | null>(initialEvalData ?? null);
  const [selectedRunId, setSelectedRunId] = useState(initialSnapshot.active_run_id);

  useEffect(() => {
    let socket: Socket | null = io(socketUrl(), { transports: ["websocket", "polling"] });
    socket.on("connect", () => {
      socket?.emit("subscribe_dashboard");
    });
    socket.on("dashboard_snapshot", (nextSnapshot: DashboardSnapshot) => {
      setSnapshot(nextSnapshot);
      setSelectedRunId((current) => {
        if (nextSnapshot.runs.some((run) => run.run_id === current)) return current;
        return nextSnapshot.active_run_id;
      });
    });
    return () => {
      socket?.close();
      socket = null;
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(async () => {
      const nextSnapshot = await api<DashboardSnapshot>("/api/dashboard").catch(() => null);
      if (nextSnapshot) setSnapshot(nextSnapshot);
      const nextEvalData = await api<EvalSnapshot>("/api/evals/latest?run_id=local-representative").catch(() => null);
      if (nextEvalData) setEvalData(nextEvalData);
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const selectedRun = useMemo(
    () => snapshot.runs.find((run) => run.run_id === selectedRunId) ?? snapshot.runs[0],
    [selectedRunId, snapshot.runs],
  );
  return (
    <div className="space-y-5">
      <section className="space-y-5">
        <div>
          <div>
            <h1 className="page-title">Clinical Evidence Overview</h1>
            <p className="page-subtitle">Track the CMS, FDA, and PubMed evidence base behind clinical policy review, labeling analysis, and biomedical literature intelligence.</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-5">
          <MetricCard label="Evidence records" value={formatNumber(selectedRun?.processed_documents)} />
          <MetricCard label="Review passages" value={formatNumber(selectedRun?.chunks_indexed)} />
          <MetricCard label="Quality pass rate" value={formatPercent(evalData?.summary?.pass_rate)} />
          <MetricCard label="Citation coverage" value={formatPercent(evalData?.summary?.doc_hit_rate)} />
          <MetricCard label="Source recall" value={formatPercent(evalData?.summary?.avg_source_recall)} />
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <div className="diagnostic-shell">
          <div className="surface-card overflow-hidden">
            <div className="surface-header">
              <div className="eyebrow">Clinical Source Library</div>
            </div>
            <div className="grid gap-4 p-5 md:grid-cols-3">
              {(selectedRun?.sources ?? []).map((source) => (
                <div key={`${selectedRun?.run_id}-${source.source_type}`} className="rounded-[24px] border border-line/70 bg-white/55 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="eyebrow">{sourceLabel(source.source_type)}</div>
                    <span className="status-pill">Ready</span>
                  </div>
                  <div className="mt-4 metric-value">{formatNumber(source.processed_documents)}</div>
                  <p className="mt-4 text-sm font-light leading-6 text-muted">{sourceLabel(source.source_type)} evidence available for cited review</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="diagnostic-shell">
          <div className="surface-card h-full p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="eyebrow">Retrieval Index</div>
                <h2 className="mt-2 section-title">Ready for review</h2>
              </div>
              <span className="status-pill bg-mint text-green">Active</span>
            </div>
            <div className="mt-6 rounded-[24px] border border-line/70 bg-white/55 p-4">
              <div className="eyebrow">Review Passages</div>
              <div className="mt-2 metric-value">{formatNumber(selectedRun?.chunks_indexed)}</div>
            </div>
            <div className="mt-4 rounded-[24px] border border-line/70 bg-sage/35 p-4">
              <div className="eyebrow">Source Coverage</div>
              <div className="mt-3 text-sm font-semibold leading-6 text-ink">CMS, FDA, and PubMed</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
