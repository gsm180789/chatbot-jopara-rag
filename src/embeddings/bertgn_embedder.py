"""
Wrapper de embeddings para mmaguero/multilingual-bert-gn-base-cased vía
Hugging Face Transformers, usando el token [CLS] como representación del
chunk.
"""

from __future__ import annotations

from typing import List

import torch
from transformers import AutoModel, AutoTokenizer

from config.settings import models


class BertGnEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or models.bertgn_model_name
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.eval()

    @torch.no_grad()
    def embed(self, text: str) -> List[float]:
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        )
        outputs = self.model(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0)
        return cls_embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]