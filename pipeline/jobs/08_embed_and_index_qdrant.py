from __future__ import annotations

import argparse
import hashlib
import json

from medintel.config import get_settings
from medintel.embeddings import embed_text
from medintel.metrics import stage
from medintel.qdrant_index import payload_for_chunk, recreate_collection, upsert_qdrant_points
from medintel.r2_storage import LocalLake, write_jsonl
from medintel import db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    settings = get_settings()
    lake = LocalLake(settings)
    stage(args.run_id, "qdrant_index", "Embedding and indexing retrieval chunks")
    collection = "medintel_healthcare_v001"
    recreate_collection(settings.qdrant_url, collection, 384)
    indexed = 0
    prepared = 0
    batch = []
    with lake.path("retrieval", "corpus", f"{args.run_id}.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            chunk = json.loads(line)
            point_id = int(hashlib.sha1(chunk["chunk_id"].encode("utf-8")).hexdigest()[:15], 16)
            batch.append({"id": point_id, "vector": embed_text(chunk["text_chunk"]), "payload": payload_for_chunk(chunk)})
            prepared += 1
            if len(batch) >= 512:
                if upsert_qdrant_points(settings.qdrant_url, collection, batch):
                    indexed += len(batch)
                batch = []
    if batch and upsert_qdrant_points(settings.qdrant_url, collection, batch):
        indexed += len(batch)
    manifest = {
        "index_id": "local-v001",
        "collection_name": collection,
        "embedding_model": settings.embedding_model,
        "vector_dim": 384,
        "indexed_chunks": indexed or prepared,
        "status": "active" if indexed else "local_manifest_only",
        "index_version": "v001",
    }
    write_jsonl(lake.path("retrieval", "index_manifests", f"{args.run_id}.jsonl"), [manifest])
    db.execute(
        """
        INSERT INTO qdrant_indexes (index_id, collection_name, source_description, embedding_model, vector_dim, indexed_chunks, status, index_version, activated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (index_id) DO UPDATE SET indexed_chunks = EXCLUDED.indexed_chunks, status = EXCLUDED.status
        """,
        (manifest["index_id"], collection, "Local real CMS/FDA/PubMed small corpus", manifest["embedding_model"], 384, manifest["indexed_chunks"], manifest["status"], "v001"),
    )
    db.update_run(args.run_id, chunks_indexed=manifest["indexed_chunks"], status="completed", current_stage="completed")
    db.execute("UPDATE pipeline_runs SET finished_at = now(), updated_at = now() WHERE run_id = %s", (args.run_id,))
    db.event(args.run_id, "qdrant_index", f"Prepared {manifest['indexed_chunks']} vectors for {collection}")


if __name__ == "__main__":
    main()
