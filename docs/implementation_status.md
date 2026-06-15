# Implementation Status

MedIntel currently implements the core clinical evidence review workflow. The next phase is retrieval-quality refinement, evaluation maturity, and deployment hardening.

## Implemented

### Data Ingestion

- Real CMS Medicare Coverage Database current Article, LCD, and NCD ZIP parsing.
- Real openFDA drug label fetching across product classes, safety terms, indications, and label updates.
- Real PubMed baseline XML gzip processing into canonical JSONL.
- Canonical source documents with source type, document ID, title, URL, dates, text, version, and metadata.

### Processing Pipeline

- Manifest creation for named runs.
- Bronze ingest.
- Silver normalization.
- Healthcare entity extraction for drugs, conditions, CPT/HCPCS-like codes, ICD-like codes, and related terms.
- Quality and safety flags.
- Retrieval corpus selection.
- Deterministic Qdrant indexing.

### Orchestration

- Dagster jobs for small real-data runs, representative runs, evaluation, and threshold gates.
- Dagster UI support for triggering runs and inspecting logs.
- Repeatable run semantics with artifact rewrites and vector upserts.

### Application

- Next.js UI with Dashboard, Intel Lens, and Signal Quality pages.
- Express API for dashboard state, source registry, evaluation summaries, indexing state, and evidence queries.
- WebSocket-backed dashboard refresh.
- Source-filtered evidence search across CMS, FDA, and PubMed.
- Citation panels and retrieval scoring details.

### Intelligence And Evaluation

- OpenAI answer generation from retrieved context.
- OpenAI reranking for production-style relevance scoring.
- Hybrid candidate selection that merges Qdrant retrieval with source-filtered lexical recall.
- 40-question representative evaluation set.
- Evaluation summary, source recall, doc hit rate, pass rate, and threshold gate.

## Current Strengths

- The project works with real public healthcare data.
- The representative corpus is large enough to exercise meaningful pipeline and retrieval behavior.
- Dagster gives visible orchestration, logs, and reruns.
- Retrieval is inspectable: users can see why a source ranked.
- The UI is focused on the actual workflow instead of a marketing shell.
- The data contract is ready for larger infrastructure without changing application semantics.

## Refinement Areas

### Retrieval Quality

PubMed-heavy questions need stronger biomedical semantic retrieval. The current hash-vector/Qdrant path plus lexical recall is useful for repeatable development, but the next quality jump should come from biomedical embeddings and a better chunking strategy for abstracts.

Recommended next steps:

- Add a production embedding model for corpus indexing.
- Store embedding model metadata in the index manifest.
- Evaluate per-source retrieval separately for CMS, FDA, and PubMed.
- Tune chunk sizes by source type.

### Evaluation

The 40-question set is a strong start. It should become a more formal benchmark.

Recommended next steps:

- Add question categories: policy code lookup, drug label safety, PubMed evidence, mixed source synthesis.
- Track source-level pass rates over time.
- Store eval history for trend charts.
- Add expected citation IDs where possible.

### CMS Policy Intelligence

CMS parsing is implemented, but the policy comparison experience should stay out of the main navigation until it can compare meaningful policy versions by topic/code.

Recommended next steps:

- Build explicit CMS topic/code grouping.
- Compare current and historical LCD/article versions.
- Generate structured policy-change summaries.
- Add citations to exact policy sections.

### FDA Coverage

FDA ingestion is real but can be broadened.

Recommended next steps:

- Expand representative query groups by therapeutic area.
- Track SPL/set ID changes over time.
- Deduplicate labels by product and effective date.
- Surface manufacturer, route, product type, and pharmacologic class in the UI.

### Packaging Polish

Recommended next steps:

- Add a concise reviewer walkthrough.
- Add an architecture image exported from the Mermaid diagram.
- Add a sample evaluation report.
- Add a concise review script with 3-5 example questions.
- Add a license note clarifying source-data licensing responsibilities.

## Not Required To Prove Value

Cloudflare R2, RunPod, and Hetzner are valuable for scale and deployment, but they are not required to validate the core engineering model. The current representative path already validates:

- real ingestion,
- Spark processing,
- orchestration,
- indexing,
- answer generation,
- reranking,
- evaluation,
- and a usable evidence UI.

Cloud should be treated as the next operating environment, not a prerequisite for product value.
