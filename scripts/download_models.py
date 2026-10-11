"""
Descarga y cachea localmente los modelos de Hugging Face que usa el
proyecto, para no depender de una descarga implícita la primera vez que
se ejecuta el pipeline real.

Uso: python scripts/download_models.py
"""

from transformers import AutoModel, AutoTokenizer

from config.settings import models


def main() -> None:
    print(f"Descargando tokenizer y modelo: {models.bertgn_model_name}")
    AutoTokenizer.from_pretrained(models.bertgn_model_name)
    AutoModel.from_pretrained(models.bertgn_model_name)
    print("Listo. Quedó cacheado en ~/.cache/huggingface/")


if __name__ == "__main__":
    main()