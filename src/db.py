"""Utilidades de conexión a PostgreSQL."""
import re

import psycopg

from config import settings


def pg_url(url: str) -> str:
    """Quita el sufijo de driver (postgresql+psycopg2://) si lo tiene."""
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def connect() -> psycopg.Connection:
    return psycopg.connect(pg_url(settings.db.url), autocommit=True)


def to_vector(values) -> str:
    """Formato de texto que pgvector acepta: [0.1,0.2,...]"""
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"