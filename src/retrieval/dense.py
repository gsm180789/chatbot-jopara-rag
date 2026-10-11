"""Recuperación Dense: similitud coseno en pgvector, filtrada por modelo."""
from dataclasses import dataclass

from src.db import connect, to_vector

TOP_K = 5
EF_SEARCH = 40


@dataclass
class RetrievedChunk:
    rank: int
    chunk_id: int
    document: str
    chunk_index: int
    score: float          # similitud coseno (1 = idéntico)
    text: str


class DenseRetriever:
    def __init__(self, model_name: str, embedder, top_k: int = TOP_K,
                 ef_search: int = EF_SEARCH) -> None:
        self.embedder = embedder
        self.top_k = top_k
        self.conn = connect()
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM embedding_models WHERE model_name = %s",
                        (model_name,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Modelo no registrado: {model_name}")
            self.model_id = int(row[0])
            cur.execute(f"SET hnsw.ef_search = {int(ef_search)}")

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        vec = to_vector(self.embedder.embed(query))
        # El id del modelo va como literal (es un entero que sale de la base):
        # un índice parcial solo se usa si el WHERE coincide con su condición.
        sql = f"""
            WITH top AS (
                SELECT chunk_id, embedding <=> %s::vector AS distance
                FROM embeddings
                WHERE embedding_model_id = {self.model_id}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            )
            SELECT c.id, d.filename, c.chunk_index, c.chunk_text, t.distance
            FROM top t
            JOIN chunks c ON c.id = t.chunk_id
            JOIN documents d ON d.id = c.document_id
            ORDER BY t.distance
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (vec, vec, self.top_k))
            rows = cur.fetchall()
        return [
            RetrievedChunk(rank=i + 1, chunk_id=r[0], document=r[1],
                           chunk_index=r[2], text=r[3], score=1.0 - float(r[4]))
            for i, r in enumerate(rows)
        ]