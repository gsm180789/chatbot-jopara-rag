"""
Wrapper de embeddings para nomic-embed-text-v1.5 (GGUF, Q4_K_M) vía
llama-cpp-python. Debe producir vectores de 768 dimensiones.

nomic-embed-text-v1.5 espera un prefijo de tarea al comienzo de cada texto:
  - documentos (indexación): "search_document: "
  - consultas (recuperación): "search_query: "
"""

from __future__ import annotations

from typing import List

from llama_cpp import Llama

from config.settings import models

DOC_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class NomicEmbedder:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or models.nomic_embed_gguf_path
        # n_ctx / n_batch amplios: el tokenizador de nomic puede generar más
        # tokens que el de BERT-gn para un mismo chunk de 512 tokens.
        self._llm = Llama(
            model_path=self.model_path,
            embedding=True,
            n_ctx=2048,
            n_batch=2048,
            n_ubatch=2048,
            verbose=False,
        )

    def _embed(self, text: str) -> List[float]:
        result = self._llm.create_embedding(text)
        return result["data"][0]["embedding"]

    def embed(self, text: str, prefix: str = QUERY_PREFIX) -> List[float]:
        """Embedding de una consulta (por defecto con prefijo de consulta)."""
        return self._embed(prefix + text)

    def embed_batch(self, texts: List[str], prefix: str = DOC_PREFIX) -> List[List[float]]:
        """Embeddings de documentos/chunks (por defecto con prefijo de documento)."""
        return [self._embed(prefix + t) for t in texts]