#!/usr/bin/env sh
set -eu
PYTHONPATH=/app/pipeline python /app/pipeline/jobs/08_embed_and_index_qdrant.py "$@"
