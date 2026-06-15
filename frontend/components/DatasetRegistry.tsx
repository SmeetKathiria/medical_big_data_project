const sourceLabels: Record<string, string> = {
  cms: "CMS",
  fda: "FDA",
  pubmed: "PubMed",
};

export function DatasetRegistry({ datasets }: { datasets: any[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {datasets.map((dataset) => (
        <div key={dataset.source_id} className="diagnostic-shell">
          <section className="surface-card min-h-44 p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="eyebrow">{sourceLabels[dataset.source_type] ?? dataset.source_type}</div>
              <span className="status-pill">Ready</span>
            </div>
            <div className="mt-4 metric-value">
              {new Intl.NumberFormat("en-US").format(dataset.document_count ?? 0)}
            </div>
            <p className="mt-4 text-sm font-light leading-6 text-muted">{sourceLabels[dataset.source_type] ?? dataset.source_type} source collection</p>
          </section>
        </div>
      ))}
    </div>
  );
}
