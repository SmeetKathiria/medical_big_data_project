# CMS Policy Workflow

CMS records are ingested from JSONL in local mode, normalized to a common document schema, scored for safety and quality, diffed across versions, and selected for retrieval when they preserve policy citations and relevant code metadata.

CMS MCD archive downloads are gated by `CMS_MCD_LICENSE_ACCEPTED=true`. The small local test path uses a real current Article subset for CPT/HCPCS `72148`. Policy diffs are generated only when multiple versions of the same CMS display document are present.

Recommended progression:

1. Run `CMS_MCD_LICENSE_ACCEPTED=true make local-e2e-small` for a small real-data evidence pipeline check.
2. Run `CMS_MCD_LICENSE_ACCEPTED=true make download-cms-mcd-current` to cache current LCD, Article, and NCD ZIPs.
3. Run the local representative Dagster job to parse current CMS archives into canonical JSONL.
4. Keep policy comparison out of the primary UI until CMS documents are grouped by code/topic and comparable version history is available.
5. For full-corpus deployment, use the same lake contract with remote storage and larger Spark workers.
