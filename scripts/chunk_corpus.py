"""Chunkea todo el corpus: python -m scripts.chunk_corpus"""
import json
from pathlib import Path

from transformers import AutoTokenizer

from config import settings
from src.ingestion.chunking import chunk_document
from src.ingestion.loaders import LOADERS, load_document

CORPUS_DIR = Path("data/corpus")
OUT_FILE = Path("data/processed/chunks.jsonl")

tokenizer = AutoTokenizer.from_pretrained(settings.models.bertgn_model_name)
tokenizer.model_max_length = 10**6

files = sorted(
    p for p in CORPUS_DIR.rglob("*")
    if p.is_file() and not p.name.startswith("~$")
)

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
total_chunks, errors, skipped = 0, [], []

with OUT_FILE.open("w", encoding="utf-8") as out:
    for path in files:
        if path.suffix.lower() not in LOADERS:
            skipped.append(path.name)
            continue
        try:
            doc = load_document(path)
            chunks = chunk_document(
                doc,
                tokenizer,
                settings.chunking.chunk_size_tokens,
                settings.chunking.chunk_overlap_tokens,
            )
        except Exception as e:
            errors.append((path.name, repr(e)))
            continue

        for c in chunks:
            out.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")
        total_chunks += len(chunks)
        print(f"{len(chunks):>3} chunks | {doc.doc_type:<4} | {path.name}")

print("-" * 60)
print(f"Archivos leídos : {len(files) - len(skipped) - len(errors)}")
print(f"Chunks totales  : {total_chunks}")
print(f"Omitidos (formato no soportado): {skipped}")
print(f"Errores         : {errors}")
print(f"Guardado en     : {OUT_FILE}")