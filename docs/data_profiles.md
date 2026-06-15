# Data Profiles

MedIntel uses one canonical lake layout at every scale:

```text
data/lake/
  raw/
  bronze/
  silver/
  gold/
  retrieval/
  reports/
  manifests/
  evals/
```

Profiles change corpus coverage and the storage backend. They do not change source schemas, Spark jobs, retrieval artifacts, evaluation files, or UI contracts.

## Profiles

| Profile | Run ID | Storage | Purpose |
| --- | --- | --- | --- |
| `local-small` | `local-real-small` | Local disk | Fast real-data smoke test for app and pipeline checks. |
| `local-representative` | `local-representative` | Local disk | Main proof profile for meaningful local evidence search and evaluation. |
| `cloud-full` | `cloud-full` | Optional R2-backed lake | Future full-corpus processing and shared deployment. |

## Local Representative Copy

The local representative copy is the best profile for demonstrating project value. It uses real source data and mirrors the same canonical format expected by larger deployments.

Run it through Dagster when possible:

```bash
PYTHONPATH=pipeline .venv/bin/python -m dagster job execute -f pipeline/dagster_defs.py -j local_representative_rag_job
```

Equivalent Make targets:

```bash
make local-representative-raw
make local-representative-pipeline
make local-representative-rag-index
```

`local-representative-raw`:

1. Downloads an official PubMed baseline slice.
2. Converts PubMed XML gzip archives into canonical PubMed JSONL.
3. Downloads current CMS Article, LCD, and NCD ZIP archives.
4. Parses CMS archives into canonical CMS JSONL.
5. Fetches a broader real openFDA drug label set across classes, safety terms, indications, and label updates.

Validated local representative state:

| Artifact | Count |
| --- | ---: |
| PubMed baseline gzip files | 50 |
| PubMed canonical records | 711,756 |
| CMS canonical records | 3,315 |
| FDA canonical records | 384 |
| Normalized documents | 715,455 |
| Indexed source records | 715,372 |

## Rerun Rules

- Reusing the same `run_id` rewrites derived lake artifacts.
- Qdrant point IDs are deterministic from `chunk_id`, so reruns update existing vectors.
- Registry tables use update/upsert behavior.
- Dagster run records are retained as execution history.

## Optional Full-Corpus Profile

The full profile should preserve the local contract:

- PubMed baseline archives under the same `raw/pubmed_baseline_*` pattern.
- Canonical source JSONL under `raw/cms/`, `raw/fda/`, and `raw/pubmed/`.
- Derived outputs under `bronze/`, `silver/`, `gold/`, `retrieval/`, `reports/`, `manifests/`, and `evals/`.
- The same application APIs and UI paths.

When scaling out, change compute and storage, not the data contract. The Spark-backed processing model is intended to carry the same workflow to TB/PB-scale corpora.
