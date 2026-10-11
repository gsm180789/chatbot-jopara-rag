"""Prueba del registro (se deshace al final, no deja datos de prueba).
Uso: python -m scripts.test_registro
"""
from src.chat.store import (
    GENERATIVE_MODEL, add_message, ensure_experiment_conditions,
    ensure_runner_session, log_turn, start_conversation,
)
from src.db import connect
from src.embeddings.nomic_embedder import NomicEmbedder
from src.retrieval.dense import DenseRetriever

NOMBRE = "nomic-embed-text-v1.5"
PREGUNTA = "¿Cuántas horas tiene la asignatura Introducción a la Matemática?"


class Deshacer(Exception):
    pass


conn = connect()

# Configuración real (esta sí queda guardada): condiciones, usuario y sesión.
condiciones = ensure_experiment_conditions(conn)
user_id, session_id = ensure_runner_session(conn)
print(f"Condiciones: {len(condiciones)} | usuario: {user_id} | sesión: {session_id}")

retriever = DenseRetriever(NOMBRE, NomicEmbedder())
chunks = retriever.retrieve(PREGUNTA)

try:
    with conn.transaction():
        conv_id = start_conversation(
            conn, user_id, session_id, condiciones[(NOMBRE, "dense")],
            "PRUEBA de registro",
        )
        log_turn(conn, conv_id, PREGUNTA, "[prueba: sin generación]", chunks)

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM messages WHERE conversation_id = %s", (conv_id,))
            n_msg = cur.fetchone()[0]
            cur.execute(
                "SELECT m.sender_role, mc.rank_position, round(mc.relevance_score::numeric, 3), "
                "d.filename FROM messages_chunks mc "
                "JOIN messages m ON m.id = mc.message_id "
                "JOIN chunks c ON c.id = mc.chunk_id "
                "JOIN documents d ON d.id = c.document_id "
                "WHERE m.conversation_id = %s ORDER BY mc.rank_position", (conv_id,))
            filas = cur.fetchall()
        print(f"\nDentro de la transacción: {n_msg} mensajes, {len(filas)} chunks asociados")
        for f in filas:
            print("  ", f)
        raise Deshacer
except Deshacer:
    pass

with conn.cursor() as cur:
    cur.execute("SELECT (SELECT count(*) FROM conversations), "
                "(SELECT count(*) FROM messages), (SELECT count(*) FROM messages_chunks)")
    print("\nTras deshacer -> conversations, messages, messages_chunks:", cur.fetchone())