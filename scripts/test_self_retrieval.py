"""Sanidad: cada chunk, usado como consulta, debería recuperarse a sí mismo.
Uso: python -m scripts.test_self_retrieval <nomic|bertgn>
"""
import sys

from config import settings
from src.db import connect
from src.embeddings.bertgn_embedder import BertGnEmbedder
from src.embeddings.nomic_embedder import NomicEmbedder
from src.retrieval.dense import DenseRetriever

MODELOS = {
    "nomic": ("nomic-embed-text-v1.5", NomicEmbedder),
    "bertgn": (settings.models.bertgn_model_name, BertGnEmbedder),
}

nombre, clase = MODELOS[sys.argv[1]]
retriever = DenseRetriever(nombre, clase())

with connect().cursor() as cur:
    cur.execute("SELECT id, chunk_text FROM chunks ORDER BY id")
    chunks = cur.fetchall()

aciertos = 0
for chunk_id, texto in chunks:
    resultado = retriever.retrieve(texto)
    if resultado and resultado[0].chunk_id == chunk_id:
        aciertos += 1

print(f"{nombre}: {aciertos}/{len(chunks)} chunks se recuperan a sí mismos en el puesto 1")