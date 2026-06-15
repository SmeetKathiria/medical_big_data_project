.PHONY: local-up local-down db-init fetch-small-data fetch-representative-sidecars download-cms-mcd-current download-cms-mcd-all parse-cms-mcd-current fetch-fda-representative download-pubmed-medium download-pubmed-representative extract-pubmed-representative spark-pubmed-medium local-representative-raw local-representative-pipeline local-representative-rag-index local-representative-rag-eval local-representative-rag-eval-gate dagster-list dagster-webserver dagster-daemon profile-data local-pipeline local-pipeline-small local-pipeline-small-from-raw local-rag-index local-rag-index-small local-e2e-small backend frontend test clean r2-check runpod-help hetzner-help

PYTHON ?= .venv/bin/python
RUN_ID ?= local-real-small
CMS_MCD_LICENSE_ACCEPTED ?= true
DAGSTER_HOME ?= $(CURDIR)/.dagster_home
NPM ?= npm
NPM_ENV ?=
RAG_EVAL_ARGS ?=
CMS_REPRESENTATIVE_MAX_ARTICLES ?= 5000
CMS_REPRESENTATIVE_MAX_LCDS ?= 5000
CMS_REPRESENTATIVE_MAX_NCDS ?= 1000
FDA_REPRESENTATIVE_PER_QUERY_LIMIT ?= 25
FDA_REPRESENTATIVE_TOTAL_LIMIT ?= 500

local-up:
	docker compose -f docker-compose.local.yml up -d

local-down:
	docker compose -f docker-compose.local.yml down

db-init:
	psql "$${DATABASE_URL:-postgresql://medintel:medintel@localhost:5432/medintel}" -f infra/hetzner/postgres_init.sql

fetch-small-data:
	PYTHONPATH=pipeline CMS_MCD_LICENSE_ACCEPTED=$(CMS_MCD_LICENSE_ACCEPTED) $(PYTHON) pipeline/jobs/00_fetch_small_sources.py --run-id local-real-small

fetch-representative-sidecars:
	PYTHONPATH=pipeline CMS_MCD_LICENSE_ACCEPTED=$(CMS_MCD_LICENSE_ACCEPTED) $(PYTHON) pipeline/jobs/00_fetch_small_sources.py --run-id local-representative --pubmed-limit 0

download-cms-mcd-current:
	PYTHONPATH=pipeline CMS_MCD_LICENSE_ACCEPTED=$(CMS_MCD_LICENSE_ACCEPTED) $(PYTHON) pipeline/jobs/00_download_cms_mcd_archives.py --run-id cms-mcd-current --dataset current_lcd --dataset current_article --dataset ncd

download-cms-mcd-all:
	PYTHONPATH=pipeline CMS_MCD_LICENSE_ACCEPTED=$(CMS_MCD_LICENSE_ACCEPTED) $(PYTHON) pipeline/jobs/00_download_cms_mcd_archives.py --run-id cms-mcd-all

parse-cms-mcd-current:
	PYTHONPATH=pipeline CMS_MCD_LICENSE_ACCEPTED=$(CMS_MCD_LICENSE_ACCEPTED) $(PYTHON) pipeline/jobs/12_cms_mcd_archives_to_raw_jsonl.py --run-id local-representative --archive-run-id cms-mcd-current --max-articles $(CMS_REPRESENTATIVE_MAX_ARTICLES) --max-lcds $(CMS_REPRESENTATIVE_MAX_LCDS) --max-ncds $(CMS_REPRESENTATIVE_MAX_NCDS) --cms-license-accepted

fetch-fda-representative:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/13_fetch_representative_fda.py --run-id local-representative --per-query-limit $(FDA_REPRESENTATIVE_PER_QUERY_LIMIT) --total-limit $(FDA_REPRESENTATIVE_TOTAL_LIMIT)

download-pubmed-medium:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/00_download_pubmed_medium.py --run-id pubmed-medium-local --target-gib $${PUBMED_MEDIUM_TARGET_GIB:-4.0} --max-files $${PUBMED_MEDIUM_MAX_FILES:-24}

download-pubmed-representative:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/00_download_pubmed_medium.py --run-id local-representative --target-gib $${PUBMED_REPRESENTATIVE_TARGET_GIB:-8.0} --max-files $${PUBMED_REPRESENTATIVE_MAX_FILES:-64}

extract-pubmed-representative:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/11_pubmed_baseline_to_raw_jsonl.py --run-id local-representative --baseline-run-id local-representative

spark-pubmed-medium:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/10_pubmed_medium_spark.py --run-id pubmed-medium-local

local-representative-raw: download-pubmed-representative extract-pubmed-representative download-cms-mcd-current parse-cms-mcd-current fetch-fda-representative

local-representative-pipeline:
	$(MAKE) local-pipeline RUN_ID=local-representative

local-representative-rag-index:
	$(MAKE) local-rag-index RUN_ID=local-representative

local-representative-rag-eval:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/09_rag_eval.py --run-id local-representative --api-url $${MEDINTEL_API_URL:-http://127.0.0.1:4000} $(RAG_EVAL_ARGS)

local-representative-rag-eval-gate:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/09_rag_eval.py --run-id local-representative --api-url $${MEDINTEL_API_URL:-http://127.0.0.1:4000} --enforce-thresholds $(RAG_EVAL_ARGS)

dagster-list:
	PYTHONPATH=pipeline $(PYTHON) -m dagster job list -f pipeline/dagster_defs.py

dagster-webserver:
	mkdir -p "$(DAGSTER_HOME)"
	DAGSTER_HOME="$(DAGSTER_HOME)" PYTHONPATH=pipeline $(PYTHON) -m dagster_webserver -f pipeline/dagster_defs.py -h 127.0.0.1 -p $${DAGSTER_PORT:-3002}

dagster-daemon:
	mkdir -p "$(DAGSTER_HOME)"
	DAGSTER_HOME="$(DAGSTER_HOME)" PYTHONPATH=pipeline .venv/bin/dagster-daemon run -f pipeline/dagster_defs.py

profile-data:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/00_profile_sources.py --run-id local-real-small

local-pipeline:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/01_create_manifest.py --run-id $(RUN_ID) --source-type all --input-uri data/lake/raw --storage-mode local
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/02_bronze_ingest.py --run-id $(RUN_ID)
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/03_normalize_sources.py --run-id $(RUN_ID)
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/04_extract_healthcare_entities.py --run-id $(RUN_ID)
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/05_quality_and_safety.py --run-id $(RUN_ID)
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/06_policy_version_diff.py --run-id $(RUN_ID)
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/07_select_retrieval_corpus.py --run-id $(RUN_ID)

local-pipeline-small: fetch-small-data profile-data
	$(MAKE) local-pipeline-small-from-raw

local-pipeline-small-from-raw: profile-data
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/01_create_manifest.py --run-id local-real-small --source-type all --input-uri data/lake/raw --storage-mode local
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/02_bronze_ingest.py --run-id local-real-small
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/03_normalize_sources.py --run-id local-real-small
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/04_extract_healthcare_entities.py --run-id local-real-small
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/05_quality_and_safety.py --run-id local-real-small
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/06_policy_version_diff.py --run-id local-real-small
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/07_select_retrieval_corpus.py --run-id local-real-small

local-rag-index:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/08_embed_and_index_qdrant.py --run-id $(RUN_ID)

local-rag-index-small:
	PYTHONPATH=pipeline $(PYTHON) pipeline/jobs/08_embed_and_index_qdrant.py --run-id local-real-small

local-e2e-small: local-pipeline-small local-rag-index-small

backend:
	cd backend && $(NPM_ENV) $(NPM) run dev

frontend:
	cd frontend && $(NPM_ENV) $(NPM) run dev

test:
	PYTHONPATH=pipeline $(PYTHON) pipeline/tests/run_tests.py
	cd backend && $(NPM_ENV) $(NPM) test

clean:
	rm -rf data/lake .pytest_cache pipeline/.pytest_cache

r2-check:
	PYTHONPATH=pipeline $(PYTHON) -m medintel.config --check-r2

runpod-help:
	@echo "Build infra/runpod/Dockerfile.worker, push it, then run jobs with RUNPOD_* env vars. See docs/runpod_setup.md."

hetzner-help:
	@echo "Copy .env to the VPS, set secrets, then run: docker compose -f docker-compose.hetzner.yml up -d"
