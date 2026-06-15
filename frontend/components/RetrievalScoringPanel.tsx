type RetrievedChunk = {
  rank?: number;
  chunk_id?: string;
  doc_id?: string;
  title?: string;
  source_type?: string;
  retrieval_mode?: string;
  score?: number;
  scoring?: {
    final_score?: number;
    vector_score?: number;
    lexical_score?: number;
    entity_score?: number;
    authority_score?: number;
    rerank_score?: number;
    rerank_reason?: string;
    matched_terms?: string[];
    matched_entities?: string[];
  };
};

function fmt(value: unknown, decimalsForIntegers = false) {
  if (typeof value !== "number") return "-";
  if (decimalsForIntegers) return value.toFixed(3);
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

function hasNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value);
}

function joined(values: string[] | undefined, fallback = "None") {
  return values?.length ? values.join(", ") : fallback;
}

function traceLabel(retrieval: any) {
  if (!retrieval) return "Clinical ranking";
  return "Hybrid retrieval · clinical ranking";
}

function selectionRationale(chunk: RetrievedChunk) {
  if (chunk.scoring?.rerank_reason) return chunk.scoring.rerank_reason;
  const terms = chunk.scoring?.matched_terms ?? [];
  const entities = chunk.scoring?.matched_entities ?? [];
  if (entities.length && terms.length) return "Selected for matching the requested identifier and supporting clinical terms.";
  if (entities.length) return "Selected for matching the requested source identifier.";
  if (terms.length) return "Selected for matching the review question language.";
  return "Selected from the available source context.";
}

export function RetrievalScoringPanel({ retrieval, chunks }: { retrieval?: any; chunks: RetrievedChunk[] }) {
  if (!chunks.length) {
    return (
      <section className="surface-card p-5">
        <h2 className="section-title">Signal Trace</h2>
        <p className="mt-2 text-sm text-muted">After the brief completes, review why specific CMS, FDA, or PubMed records were selected.</p>
      </section>
    );
  }

  const showRerank = chunks.some((chunk) => hasNumber(chunk.scoring?.rerank_score));
  const showVector = chunks.some((chunk) => hasNumber(chunk.scoring?.vector_score));

  return (
    <div className="diagnostic-shell">
      <section className="surface-card overflow-hidden">
        <div className="surface-header">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="section-title">Signal Trace</h2>
            <span className="status-pill">
              {traceLabel(retrieval)}
            </span>
          </div>
          {retrieval?.formula && <p className="mt-2 text-xs leading-5 text-muted">Shows the selected evidence, matched clinical terms, and ranking rationale used to assemble the brief.</p>}
        </div>
        <div className="responsive-table">
          <table className="data-table signal-table min-w-[820px]">
            <colgroup>
              <col className="w-14" />
              <col className="w-20" />
              <col className="w-20" />
              {showRerank && <col className="w-20" />}
              {showVector && <col className="w-20" />}
              <col className="w-20" />
              <col className="w-20" />
              <col className="w-24" />
              <col className="w-36" />
              <col className="w-36" />
              <col className="w-64" />
              <col className="w-56" />
            </colgroup>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Source</th>
                <th>Score</th>
                {showRerank && <th>Rerank</th>}
                {showVector && <th>Vector</th>}
                <th>Lexical</th>
                <th>Entity</th>
                <th>Authority</th>
                <th>Matched terms</th>
                <th>Matched entities</th>
                <th>Selection rationale</th>
                <th>Document</th>
              </tr>
            </thead>
            <tbody>
              {chunks.map((chunk, index) => (
                <tr key={chunk.chunk_id ?? `${chunk.doc_id}-${index}`}>
                  <td className="font-semibold text-ink">{chunk.rank ?? index + 1}</td>
                  <td className="font-semibold uppercase text-green">{chunk.source_type}</td>
                  <td className="font-semibold text-ink">{fmt(chunk.scoring?.final_score ?? chunk.score, showRerank)}</td>
                  {showRerank && <td className="font-semibold text-green">{fmt(chunk.scoring?.rerank_score, true)}</td>}
                  {showVector && <td>{fmt(chunk.scoring?.vector_score)}</td>}
                  <td>{fmt(chunk.scoring?.lexical_score)}</td>
                  <td>{fmt(chunk.scoring?.entity_score)}</td>
                  <td>{fmt(chunk.scoring?.authority_score)}</td>
                  <td className="max-w-36 text-muted"><div className="cell-clamp-2">{joined(chunk.scoring?.matched_terms)}</div></td>
                  <td className="max-w-36 text-muted"><div className="cell-clamp-2">{joined(chunk.scoring?.matched_entities)}</div></td>
                  <td className="max-w-64 text-muted"><div className="cell-clamp">{selectionRationale(chunk)}</div></td>
                  <td className="max-w-64">
                    <div className="cell-clamp-2 font-semibold text-ink">{chunk.title}</div>
                    <div className="mt-1 text-muted">{chunk.doc_id}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
