function pct(value: unknown) {
  if (typeof value !== "number") return "-";
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: unknown) {
  if (typeof value !== "number") return "-";
  return new Intl.NumberFormat("en-US").format(value);
}

function thresholdLabel(ok: boolean | undefined) {
  return ok ? "Meets target" : "Below target";
}

const sourceLabels: Record<string, string> = {
  cms: "CMS",
  fda: "FDA",
  pubmed: "PubMed",
  mixed: "Mixed",
  unknown: "Unclassified",
};

export function EvalDashboard({ evalData }: { evalData: any }) {
  const summary = evalData?.summary ?? {};
  const thresholds = summary.thresholds ?? {};
  const status = summary.threshold_status ?? {};
  const failed = evalData?.failed_results ?? [];
  const breakdown = evalData?.failure_breakdown ?? {};

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <div className="diagnostic-shell">
          <div className="surface-card p-5">
            <div className="eyebrow">Quality Checks</div>
            <div className="mt-3 metric-value">{num(summary.questions)}</div>
          </div>
        </div>
        <div className="diagnostic-shell">
          <div className="surface-card p-5">
            <div className="eyebrow">Quality Pass Rate</div>
            <div className="mt-3 metric-value text-green">{pct(summary.pass_rate)}</div>
          </div>
        </div>
        <div className="diagnostic-shell">
          <div className="surface-card p-5">
            <div className="eyebrow">Citation Coverage</div>
            <div className="mt-3 metric-value">{pct(summary.doc_hit_rate)}</div>
          </div>
        </div>
        <div className="diagnostic-shell">
          <div className="surface-card p-5">
            <div className="eyebrow">Source Recall</div>
            <div className="mt-3 metric-value">{pct(summary.avg_source_recall)}</div>
          </div>
        </div>
      </div>

      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
        <section className="surface-card min-w-0 overflow-hidden">
          <div className="surface-header">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="section-title">Validation Gate</h2>
              <span className="status-pill">Curated review set</span>
            </div>
            <p className="mt-2 text-sm font-light leading-6 text-muted">Benchmarked against curated healthcare review checks for citation coverage, source recall, and answer completeness.</p>
          </div>
          <div className="responsive-table">
            <table className="data-table min-w-[560px]">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Actual</th>
                  <th>Target</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="font-semibold text-ink">Validation pass rate</td>
                  <td>{pct(summary.pass_rate)}</td>
                  <td>{pct(thresholds.min_pass_rate)}</td>
                  <td><span className="status-pill">{thresholdLabel(status.pass_rate_ok)}</span></td>
                </tr>
                <tr>
                  <td className="font-semibold text-ink">Citation coverage</td>
                  <td>{pct(summary.doc_hit_rate)}</td>
                  <td>{pct(thresholds.min_doc_hit_rate)}</td>
                  <td><span className="status-pill">{thresholdLabel(status.doc_hit_rate_ok)}</span></td>
                </tr>
                <tr>
                  <td className="font-semibold text-ink">Source recall</td>
                  <td>{pct(summary.avg_source_recall)}</td>
                  <td>{pct(thresholds.min_source_recall)}</td>
                  <td><span className="status-pill">{thresholdLabel(status.source_recall_ok)}</span></td>
                </tr>
                <tr>
                  <td className="font-semibold text-ink">Response time</td>
                  <td>{typeof summary.avg_latency_ms === "number" ? `${summary.avg_latency_ms.toFixed(0)} ms` : "-"}</td>
                  <td>-</td>
                  <td><span className="status-pill">Tracked</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="surface-card min-w-0 overflow-hidden">
          <div className="surface-header">
            <h2 className="section-title">Checks by Source</h2>
          </div>
          <div className="grid gap-3 p-5">
            {Object.keys(sourceLabels).map((key) => (
              <div key={key} className="flex items-center justify-between rounded-[24px] border border-line/70 bg-white/50 p-4">
                <span className="text-sm font-semibold leading-5 text-ink">{sourceLabels[key]}</span>
                <span className="metric-value-compact">{breakdown[key] ?? 0}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="diagnostic-shell">
        <div className="surface-card overflow-hidden">
          <div className="surface-header">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="section-title">Checks Requiring Review</h2>
              <span className="status-pill">{failed.length} checks</span>
            </div>
          </div>
          <div className="responsive-table">
            <table className="data-table min-w-[760px]">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Review question</th>
                  <th>Citation coverage</th>
                  <th>Source recall</th>
                  <th>Answer coverage</th>
                </tr>
              </thead>
              <tbody>
                {failed.map((result: any) => (
                  <tr key={result.id}>
                    <td className="font-semibold text-green">{result.id}</td>
                    <td className="max-w-md font-semibold text-ink">{result.question}</td>
                    <td>{result.doc_hit ? "Yes" : "No"}</td>
                    <td>{pct(result.source_recall)}</td>
                    <td>{pct(result.answer_term_recall)}</td>
                  </tr>
                ))}
                {!failed.length && (
                  <tr>
                    <td colSpan={5} className="text-muted">All review checks meet the current criteria.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}
