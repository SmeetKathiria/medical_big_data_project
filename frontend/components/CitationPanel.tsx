export function CitationPanel({ citations }: { citations: any[] }) {
  function sourceType(citation: any) {
    return String(citation.source_type ?? "").toLowerCase();
  }

  function displayTitle(citation: any) {
    const title = String(citation.title ?? "Untitled source").trim();
    if (sourceType(citation) === "fda" && title && !title.toLowerCase().includes("label")) {
      return `${title} drug label`;
    }
    return title;
  }

  function metaLabel(citation: any) {
    const source = String(citation.source_type ?? "source").toUpperCase();
    const version = String(citation.version ?? "").trim();
    if (sourceType(citation) === "fda") return version ? `${source} label · Set ID ${version}` : `${source} label`;
    return version ? `${source} · ${version}` : source;
  }

  function docLabel(citation: any) {
    const docId = String(citation.doc_id ?? "").trim();
    if (!docId) return "";
    return `Document ID ${docId}`;
  }

  function citationHref(citation: any) {
    const url = String(citation.url ?? "");
    if (sourceType(citation) !== "fda") return url;
    if (url && !url.includes("api.fda.gov")) return url;
    const title = String(citation.title ?? "").trim();
    if (!title || title.toLowerCase() === "fda drug label") return "";
    return `https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=${encodeURIComponent(title)}`;
  }

  return (
    <div className="rounded-[28px] border border-line/70 bg-white/35 p-3">
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <div className="eyebrow">Cited Documents</div>
        <span className="status-pill h-7 px-3">{citations.length} sources</span>
      </div>
      <div className="max-h-[232px] space-y-2 overflow-y-auto pr-1">
        {citations.map((citation) => {
          const href = citationHref(citation);
          const className = "block rounded-[24px] border border-line/70 bg-panel/88 p-4 text-sm font-light leading-6 shadow-[inset_0_1px_2px_rgba(255,255,255,0.76),0_1px_2px_rgba(28,50,45,0.05)] backdrop-blur transition hover:-translate-y-0.5 hover:border-green/45 hover:bg-mint";
          const content = (
            <>
              <div className="font-semibold text-ink">{displayTitle(citation)}</div>
              <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{metaLabel(citation)}</div>
              {docLabel(citation) && <div className="mt-1 text-[11px] font-medium text-muted">{docLabel(citation)}</div>}
              {!href && <div className="mt-2 text-[11px] text-muted">Label context is available in the MedIntel ranking trace.</div>}
            </>
          );
          return href ? (
            <a key={`${citation.doc_id}-${citation.version}`} href={href} target="_blank" rel="noreferrer" className={className}>
              {content}
            </a>
          ) : (
            <div key={`${citation.doc_id}-${citation.version}`} className={className}>
              {content}
            </div>
          );
        })}
      </div>
    </div>
  );
}
