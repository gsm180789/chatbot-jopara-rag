"""Prueba rápida del loader: python -m scripts.test_loader <ruta_archivo>"""
import sys

from src.ingestion.loaders import load_document

doc = load_document(sys.argv[1])
print(f"Archivo : {doc.source}  ({doc.doc_type})")
print(f"Metadatos: {doc.metadata}")
print(f"Caracteres: {len(doc.text)}")
print("-" * 60)
print(doc.text[:1500])