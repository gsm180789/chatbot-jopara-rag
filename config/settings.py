import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class DatabaseSettings:
    url: str = os.getenv("DATABASE_URL", "")

@dataclass(frozen=True)
class ModelPaths:
    gemma_gguf_path: str = os.getenv("GEMMA_GGUF_PATH", "")
    nomic_embed_gguf_path: str = os.getenv("NOMIC_EMBED_GGUF_PATH", "")
    bertgn_model_name: str = os.getenv("BERTGN_MODEL_NAME", "mmaguero/multilingual-bert-gn-base-cased")

@dataclass(frozen=True)
class ChunkingSettings:
    chunk_size_tokens: int = int(os.getenv("CHUNK_SIZE_TOKENS", "512"))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "51"))

@dataclass(frozen=True)
class HNSWSettings:
    m: int = int(os.getenv("HNSW_M", "16"))
    ef_construction: int = int(os.getenv("HNSW_EF_CONSTRUCTION", "64"))
    ef_search: int = int(os.getenv("HNSW_EF_SEARCH", "40"))

@dataclass(frozen=True)
class GenerationSettings:
    temperature: float = float(os.getenv("GEN_TEMPERATURE", "0.7"))
    top_p: float = float(os.getenv("GEN_TOP_P", "0.9"))
    top_k: int = int(os.getenv("GEN_TOP_K", "40"))
    max_tokens: int = int(os.getenv("GEN_MAX_TOKENS", "512"))

db = DatabaseSettings()
models = ModelPaths()
chunking = ChunkingSettings()
hnsw = HNSWSettings()
generation = GenerationSettings()