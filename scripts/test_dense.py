"""Prueba de recuperación Dense.
Uso: python -m scripts.test_dense <nomic|bertgn> "texto de la consulta"
"""
import sys

from config import settings
from src.embeddings.bertgn_embedder import BertGnEmbedder
from src.embeddings.nomic_embedder import NomicEmbedder
from src.retrieval.dense import DenseRetriever

MODELOS = {
    "nomic": ("nomic-embed-text-v1.5", NomicEmbedder),
    "bertgn": (settings.models.bertgn_model_name, BertGnEmbedder),
}

clave, consulta = sys.argv[1], sys.argv[2]
nombre, clase = MODELOS[clave]

retriever = DenseRetriever(nombre, clase())
print(f"Modelo: {nombre} | consulta: {consulta!r}\n")
for r in retriever.retrieve(consulta):
    vista = r.text[:90].replace("\n", " ")
    print(f"{r.rank}. [{r.score:.3f}] {r.document} (chunk {r.chunk_index})\n     {vista}...")