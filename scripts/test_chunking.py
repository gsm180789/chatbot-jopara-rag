"""Prueba de chunking: python -m scripts.test_chunking <ruta_archivo>"""
import sys

from transformers import AutoTokenizer

from config import settings
from src.ingestion.chunking import chunk_document
from src.ingestion.loaders import load_document

tokenizer = AutoTokenizer.from_pretrained(settings.models.bertgn_model_name)
tokenizer.model_max_length = 10**6  # evita el aviso de "secuencia muy larga"

doc = load_document(sys.argv[1])
chunks = chunk_document(
    doc,
    tokenizer,
    settings.chunking.chunk_size_tokens,
    settings.chunking.chunk_overlap_tokens,
)

print(f"{doc.source}: {len(chunks)} chunks")
for c in chunks:
    print(f"  [{c.chunk_index}] {c.n_tokens} tokens | {c.text[:70]!r}")