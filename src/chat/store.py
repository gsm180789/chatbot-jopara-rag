"""Registro de conversaciones, mensajes y chunks recuperados."""
from src.retrieval.dense import RetrievedChunk

GENERATIVE_MODEL = "Gemma-2-9B-IT-SimPO-Q4_K_M"
EMBEDDING_MODELS = [
    "nomic-embed-text-v1.5",
    "mmaguero/multilingual-bert-gn-base-cased",
]
TECHNIQUES = ["dense", "hybrid"]

RUNNER_ROLE = "experimenter"
RUNNER_USER = "experiment_runner"
RUNNER_TOKEN = "experiment-session"


def _get_or_create(conn, select_sql, select_params, insert_sql, insert_params):
    with conn.cursor() as cur:
        cur.execute(select_sql, select_params)
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(insert_sql, insert_params)
        return cur.fetchone()[0]


def ensure_experiment_conditions(conn) -> dict[tuple[str, str], int]:
    """Crea (si faltan) las 4 condiciones: 2 embeddings x 2 técnicas."""
    ids = {}
    for emb in EMBEDDING_MODELS:
        for tech in TECHNIQUES:
            ids[(emb, tech)] = _get_or_create(
                conn,
                "SELECT id FROM experiment_conditions WHERE embedding_model = %s "
                "AND retrieval_technique = %s AND generative_model = %s",
                (emb, tech, GENERATIVE_MODEL),
                "INSERT INTO experiment_conditions "
                "(embedding_model, retrieval_technique, generative_model) "
                "VALUES (%s, %s, %s) RETURNING id",
                (emb, tech, GENERATIVE_MODEL),
            )
    return ids


def ensure_runner_session(conn) -> tuple[int, int]:
    """Usuario técnico y sesión para las corridas. Devuelve (user_id, session_id)."""
    role_id = _get_or_create(
        conn,
        "SELECT id FROM roles WHERE role_name = %s", (RUNNER_ROLE,),
        "INSERT INTO roles (role_name, description) VALUES (%s, %s) RETURNING id",
        (RUNNER_ROLE, "Usuario técnico para las corridas experimentales"),
    )
    user_id = _get_or_create(
        conn,
        "SELECT id FROM users WHERE username = %s", (RUNNER_USER,),
        "INSERT INTO users (role_id, username, password_hash, full_name) "
        "VALUES (%s, %s, '!', %s) RETURNING id",
        (role_id, RUNNER_USER, "Ejecutor de experimentos"),
    )
    session_id = _get_or_create(
        conn,
        "SELECT id FROM sessions WHERE user_id = %s AND token_hash = %s",
        (user_id, RUNNER_TOKEN),
        "INSERT INTO sessions (user_id, token_hash, expires_at) "
        "VALUES (%s, %s, now() + interval '10 years') RETURNING id",
        (user_id, RUNNER_TOKEN),
    )
    return user_id, session_id


def start_conversation(conn, user_id: int, session_id: int,
                       condition_id: int, title: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (session_id, user_id, experiment_condition_id, title) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (session_id, user_id, condition_id, title),
        )
        return cur.fetchone()[0]


def add_message(conn, conversation_id: int, sender_role: str, content: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO messages (conversation_id, sender_role, content) "
            "VALUES (%s, %s, %s) RETURNING id",
            (conversation_id, sender_role, content),
        )
        return cur.fetchone()[0]


def link_chunks(conn, message_id: int, retrieved: list[RetrievedChunk]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO messages_chunks (message_id, chunk_id, relevance_score, rank_position) "
            "VALUES (%s, %s, %s, %s)",
            [(message_id, r.chunk_id, r.score, r.rank) for r in retrieved],
        )


def log_turn(conn, conversation_id: int, question: str, answer: str,
             retrieved: list[RetrievedChunk]) -> int:
    """Registra un turno completo de forma atómica: pregunta, respuesta y
    chunks que la sustentaron. Devuelve el id del mensaje del asistente."""
    with conn.transaction():
        add_message(conn, conversation_id, "user", question)
        answer_id = add_message(conn, conversation_id, "assistant", answer)
        link_chunks(conn, answer_id, retrieved)
        with conn.cursor() as cur:
            cur.execute("UPDATE conversations SET updated_at = now() WHERE id = %s",
                        (conversation_id,))
    return answer_id