"""Partición de documentos en chunks por tokens, con solapamiento."""
from dataclasses import dataclass, field

from src.ingestion.loaders import LoadedDocument


@dataclass
class Chunk:
    text: str
    source: str
    doc_type: str
    chunk_index: int
    n_tokens: int
    start_token: int
    end_token: int
    metadata: dict = field(default_factory=dict)


def chunk_document(
    doc: LoadedDocument, tokenizer, chunk_size: int, overlap: int
) -> list[Chunk]:
    """Divide el texto en ventanas de `chunk_size` tokens, avanzando
    `chunk_size - overlap` tokens cada vez.

    Se corta el texto original usando las posiciones (offsets) de cada
    token, así el chunk conserva el texto exacto, sin decodificar.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor que chunk_size")

    enc = tokenizer(
        doc.text, add_special_tokens=False, return_offsets_mapping=True
    )
    offsets = enc["offset_mapping"]
    n = len(offsets)
    step = chunk_size - overlap

    chunks: list[Chunk] = []
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        text = doc.text[offsets[start][0] : offsets[end - 1][1]].strip()
        if text:
            chunks.append(
                Chunk(
                    text=text,
                    source=doc.source,
                    doc_type=doc.doc_type,
                    chunk_index=len(chunks),
                    n_tokens=end - start,
                    start_token=start,
                    end_token=end,
                    metadata=dict(doc.metadata),
                )
            )
        if end == n:
            break
        start += step
    return chunks