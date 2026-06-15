# Runbook

This runbook is optimized for local product validation. Use Dagster for data processing so pipeline progress and logs stay visible.

## Local Services

Start local infrastructure:

```bash
make local-up
make db-init
```

Start the application:

```bash
make backend
make frontend
```

Open:

- App: `http://127.0.0.1:3000`
- API health: `http://127.0.0.1:4000/api/health`

## Dagster

List jobs:

```bash
make dagster-list
```

Start Dagster UI:

```bash
DAGSTER_PORT=3002 make dagster-webserver
```

Start the daemon in a second terminal so UI-triggered runs execute:

```bash
make dagster-daemon
```

Open `http://127.0.0.1:3002`.

## Pipeline Jobs

Small real-data smoke run:

```bash
PYTHONPATH=pipeline .venv/bin/python -m dagster job execute -f pipeline/dagster_defs.py -j local_real_small_rag_job
```

Representative local run:

```bash
PUBMED_REPRESENTATIVE_TARGET_GIB=8.0 PYTHONPATH=pipeline .venv/bin/python -m dagster job execute -f pipeline/dagster_defs.py -j local_representative_rag_job
```

The representative job downloads/parses real CMS/FDA/PubMed inputs, runs the Spark-backed pipeline, builds the evidence corpus, and indexes Qdrant.

## Evaluation

Run the local representative evaluation:

```bash
PYTHONPATH=pipeline .venv/bin/python -m dagster job execute -f pipeline/dagster_defs.py -j local_representative_rag_eval_job
```

Run the threshold gate:

```bash
PYTHONPATH=pipeline .venv/bin/python -m dagster job execute -f pipeline/dagster_defs.py -j local_representative_rag_eval_gate_job
```

For a quick smoke evaluation:

```bash
RAG_EVAL_ARGS="--limit 3" PYTHONPATH=pipeline .venv/bin/python -m dagster job execute -f pipeline/dagster_defs.py -j local_representative_rag_eval_job
```

The question bank lives at:

```text
pipeline/evals/local_representative_questions.jsonl
```

Results are written to:

```text
data/lake/evals/local-representative/latest_summary.json
data/lake/evals/local-representative/latest_results.jsonl
```

The Quality page reads those latest files.

## Retrieval And Ranking

MedIntel Lens retrieval uses `hybrid_v2`:

1. Source-filtered Qdrant candidate retrieval.
2. Source-filtered streaming lexical candidate retrieval for exact term/entity recall.
3. Candidate merge and deterministic deduplication.
4. OpenAI reranking when `OPENAI_API_KEY` and `RERANK_PROVIDER` or `LLM_PROVIDER` are enabled.
5. Citation-grounded answer generation from the final ranked context.

The UI exposes final score, rerank reason, vector score, lexical score, entity score, authority score, matched terms, and matched entities.

## Rerun Behavior

Local runs are designed to be repeatable:

- Raw source fetchers reuse existing files unless a force-refresh path is used.
- Derived lake artifacts are rewritten for the same `run_id`.
- Qdrant upserts deterministic point IDs from `chunk_id`.
- Postgres registry rows are updated/upserted.
- Dagster run history appends in `.dagster_home/`; it is orchestration history, not duplicated data.

## CMS License Note

CMS Medicare Coverage Database downloads can include CPT/CDT/UB-04-related terms. Run CMS jobs only when authorized:

```bash
CMS_MCD_LICENSE_ACCEPTED=true make download-cms-mcd-current
CMS_MCD_LICENSE_ACCEPTED=true make parse-cms-mcd-current
```

## Cloud Scale

Cloudflare R2, RunPod, and Hetzner are optional scale paths. Use them when the goal is full-corpus processing or shared deployment. Local validation should continue to use the same lake layout and run contracts.
