CREATE TABLE IF NOT EXISTS healthcare_sources (
  source_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  name TEXT NOT NULL,
  source_uri TEXT,
  version TEXT,
  effective_date DATE,
  loaded_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  current_stage TEXT,
  total_bytes BIGINT DEFAULT 0,
  processed_bytes BIGINT DEFAULT 0,
  documents_read BIGINT DEFAULT 0,
  documents_kept BIGINT DEFAULT 0,
  documents_rejected BIGINT DEFAULT 0,
  entities_extracted BIGINT DEFAULT 0,
  chunks_selected BIGINT DEFAULT 0,
  chunks_indexed BIGINT DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pipeline_events (
  id SERIAL PRIMARY KEY,
  run_id TEXT,
  stage TEXT,
  level TEXT,
  message TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS healthcare_documents (
  doc_id TEXT PRIMARY KEY,
  source_id TEXT,
  source_type TEXT,
  title TEXT,
  url TEXT,
  publication_date DATE,
  effective_date DATE,
  version TEXT,
  text_uri TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS medical_entities (
  id SERIAL PRIMARY KEY,
  doc_id TEXT,
  entity_type TEXT,
  entity_value TEXT,
  normalized_value TEXT,
  context TEXT,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_diffs (
  diff_id TEXT PRIMARY KEY,
  source_type TEXT,
  topic TEXT,
  old_version TEXT,
  new_version TEXT,
  summary TEXT,
  diff_json JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qdrant_indexes (
  index_id TEXT PRIMARY KEY,
  collection_name TEXT NOT NULL,
  source_description TEXT,
  embedding_model TEXT,
  vector_dim INTEGER,
  indexed_chunks BIGINT,
  status TEXT,
  index_version TEXT,
  activated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag_queries (
  id SERIAL PRIMARY KEY,
  query TEXT NOT NULL,
  answer TEXT,
  citations JSONB,
  retrieved_context JSONB,
  latency_ms INTEGER,
  feedback TEXT,
  created_at TIMESTAMP DEFAULT now()
);
