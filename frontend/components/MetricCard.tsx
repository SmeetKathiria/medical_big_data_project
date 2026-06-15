export function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="diagnostic-shell">
      <div className="surface-card min-h-32 p-5">
        <div className="eyebrow">{label}</div>
        <div className="mt-3 metric-value">{value}</div>
        <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-white/70">
          <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-green via-sage to-amber" />
        </div>
      </div>
    </div>
  );
}
