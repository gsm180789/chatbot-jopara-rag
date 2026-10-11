"""
Wrapper del modelo generativo Gemma-2-9B-IT-SimPO-Jopara-GGUF (Q4_K_M) vía
llama-cpp-python. Es fijo entre las 4 condiciones experimentales: el objeto
de evaluación es el retriever, no el generador.
"""

from __future__ import annotations

from typing import List

from llama_cpp import Llama

from config.settings import generation, models


class GemmaGenerator:
    def __init__(self, model_path: str | None = None, n_gpu_layers: int = 0) -> None:
        self.model_path = model_path or models.gemma_gguf_path
        self._llm = Llama(
            model_path=self.model_path,
            n_ctx=4096,
            n_gpu_layers=n_gpu_layers, # Despues de la primera ejecución
            verbose=False,
        )

    def generate(self, prompt: str, context_chunks: List[str]) -> str:
        full_prompt = self._build_prompt(prompt, context_chunks)
        output = self._llm(
            full_prompt,
            temperature=generation.temperature,
            top_p=generation.top_p,
            top_k=generation.top_k,
            max_tokens=generation.max_tokens,
            stop=["<end_of_turn>"], # Stop para cortar la generación de texto innecesario
        )
        return output["choices"][0]["text"].strip()

    @staticmethod
    def _build_prompt(query: str, context_chunks: List[str]) -> str:
        context = "\n\n".join(context_chunks)
        user_turn = f"Contexto:\n{context}\n\nPregunta: {query}" if context else f"Pregunta: {query}"
        return (
            f"<start_of_turn>user\n{user_turn}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )