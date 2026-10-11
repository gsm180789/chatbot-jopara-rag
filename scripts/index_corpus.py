"""Indexa el corpus: python -m scripts.index_corpus

Carga documentos y chunks en PostgreSQL y genera los embeddings con cada
modelo. Es repetible: no duplica filas si se ejecuta dos veces.
"""
import gc
import json
import re
from pathlib import Path

import psycopg

from config import settings
from src.embeddings.bertgn_embedder import BertGnEmbedder
from src.embeddings.nomic_embedder import NomicEmbedder

CHUNKS_FILE = Path("data/processed/chunks.jsonl")
CONFIG_NAME = "fixed_512_51"
BATCH_SIZE = 8

# (nombre en la tabla embedding_models, dimensiones, clase del embedder)
MODELS = [
    ("nomic-embed-text-v1.5", 768, NomicEmbedder),
    (settings.models.bertgn_model_name, 768, BertGnEmbedder),
]


def pg_url(url: str) -> str:
    """Quita el sufijo de driver (postgresql+psycopg2://) si lo tiene."""
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def to_vector(values) -> str:
    """Formato de texto que pgvector acepta: [0.1,0.2,...]"""
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"


rows = [json.loads(line) for line in CHUNKS_FILE.open(encoding="utf-8")]
size = settings.chunking.chunk_size_tokens
overlap = settings.chunking.chunk_overlap_tokens

with psycopg.connect(pg_url(settings.db.url)) as conn:
    cur = conn.cursor()

    # 1) Configuración de chunking
    cur.execute("SELECT id FROM chunk_configs WHERE name = %s", (CONFIG_NAME,))
    found = cur.fetchone()
    if found:
        config_id = found[0]
    else:
        cur.execute(
            "INSERT INTO chunk_configs (name, chunk_size, overlap, overlap_percentage) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (CONFIG_NAME, size, overlap, round(100 * overlap / size, 2)),
        )
        config_id = cur.fetchone()[0]

    # 2) Documentos y chunks
    doc_ids: dict[str, int] = {}
    new_chunks = 0
    for r in rows:
        path = r["metadata"]["path"]
        if path not in doc_ids:
            cur.execute("SELECT id FROM documents WHERE file_path = %s", (path,))
            found = cur.fetchone()
            if found:
                doc_ids[path] = found[0]
            else:
                cur.execute(
                    "INSERT INTO documents (filename, file_type, file_path) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (r["source"], r["doc_type"], path),
                )
                doc_ids[path] = cur.fetchone()[0]

        cur.execute(
            "SELECT 1 FROM chunks WHERE document_id = %s "
            "AND chunk_config_id = %s AND chunk_index = %s",
            (doc_ids[path], config_id, r["chunk_index"]),
        )
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO chunks (document_id, chunk_config_id, format, chunk_index, "
                "chunk_text, start_token_offset, end_token_offset) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (doc_ids[path], config_id, r["doc_type"], r["chunk_index"],
                 r["text"], r["start_token"], r["end_token"]),
            )
            new_chunks += 1
    conn.commit()
    print(f"Documentos: {len(doc_ids)} | chunks nuevos insertados: {new_chunks}")

    # 3) Embeddings, un modelo a la vez (para no ocupar toda la memoria)
    for model_name, dims, embedder_cls in MODELS:
        cur.execute(
            "INSERT INTO embedding_models (model_name, dimensions) VALUES (%s, %s) "
            "ON CONFLICT (model_name) DO NOTHING",
            (model_name, dims),
        )
        cur.execute("SELECT id FROM embedding_models WHERE model_name = %s", (model_name,))
        model_id = cur.fetchone()[0]

        cur.execute(
            "SELECT c.id, c.chunk_text FROM chunks c "
            "WHERE c.chunk_config_id = %s AND NOT EXISTS ("
            "  SELECT 1 FROM embeddings e "
            "  WHERE e.chunk_id = c.id AND e.embedding_model_id = %s) "
            "ORDER BY c.id",
            (config_id, model_id),
        )
        pending = cur.fetchall()
        if not pending:
            print(f"{model_name}: ya tiene todos los embeddings, se omite.")
            continue

        print(f"{model_name}: generando {len(pending)} embeddings...")
        embedder = embedder_cls()
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i : i + BATCH_SIZE]
            vectors = embedder.embed_batch([text for _, text in batch])
            for (chunk_id, _), vec in zip(batch, vectors):
                assert len(vec) == dims, f"{len(vec)} dimensiones, se esperaban {dims}"
                cur.execute(
                    "INSERT INTO embeddings (chunk_id, embedding_model_id, embedding) "
                    "VALUES (%s, %s, %s::vector) "
                    "ON CONFLICT (chunk_id, embedding_model_id) DO NOTHING",
                    (chunk_id, model_id, to_vector(vec)),
                )
        conn.commit()

        del embedder
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

    # 4) Resumen
    cur.execute("SELECT count(*) FROM documents")
    n_docs = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM chunks")
    n_chunks = cur.fetchone()[0]
    cur.execute(
        "SELECT m.model_name, count(*) FROM embeddings e "
        "JOIN embedding_models m ON m.id = e.embedding_model_id GROUP BY m.model_name"
    )
    print("-" * 60)
    print(f"documents: {n_docs} | chunks: {n_chunks}")
    for name, n in cur.fetchall():
        print(f"embeddings [{name}]: {n}")