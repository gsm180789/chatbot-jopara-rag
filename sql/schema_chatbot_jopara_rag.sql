-- ============================================================================
-- Chatbot Jopará RAG — Schema de base de datos
-- Generado a partir de 4 DER de draw.io:
--   DER1_Chatbot_29082026.drawio        -> ROLES, USERS, SESSIONS,
--                                          EXPERIMENT_CONDITIONS, CONVERSATIONS,
--                                          MESSAGES, MESSAGES_CHUNKS
--   DER2_Corpus_Indexado_30082026.drawio -> DOCUMENTS, CHUNK_CONFIGS, CHUNKS,
--                                          EMBEDDING_MODELS, EMBEDDINGS
--   DER3_Evaluacion_30082026.drawio      -> GOLD_STANDARD_QUERIES,
--                                          RELEVANT_CHUNKS, RETRIEVAL_RESULTS,
--                                          EVALUATION_METRICS
--   DER4_Rendimiento_30082026.drawio     -> PERFORMANCE_METRICS
--
-- Total: 17 tablas (coincide con el conteo documentado en el Capítulo 3).
--
-- ============================================================================
-- ASUNCIONES DOCUMENTADAS (los DER no especifican estos detalles; se
-- completaron con valores razonables — revisar antes de usar en producción):
--
--   1. Longitud de VARCHAR: los DER no indican longitud. Se usó VARCHAR(255)
--      como default, EXCEPTO donde el contenido es evidentemente más corto
--      (hashes, códigos de idioma, roles) o más largo (rutas de archivo).
--   2. created_at / updated_at: se agregó DEFAULT CURRENT_TIMESTAMP en todas
--      las columnas *_at que no tenían un valor por defecto explícito en el
--      diagrama. Ajustar si tu pipeline prefiere insertar el timestamp desde
--      la aplicación en vez de la base.
--   3. CONVERSATIONS.session_id -> SESSIONS.id: el DER marca esta columna
--      como [FK] en la tabla, pero no dibuja la flecha de relación
--      explícitamente (solo se dibujó la flecha SESSIONS.user_id ->
--      CONVERSATIONS.user_id). Se agregó el FK por convención de nombre.
--   4. SESSIONS: confirmado por Silvia como clave primaria compuesta
--      (id, user_id), tal como está dibujado en el DER. Como CONVERSATIONS
--      referencia sessions(id) de forma aislada, se agregó una restricción
--      UNIQUE sobre `id` además de la PK compuesta — Postgres exige que toda
--      columna referenciada por una FK externa sea única por sí sola, y una
--      PK compuesta no garantiza eso para una sola de sus columnas.
--   5. GOLD_STANDARD_QUERIES.split y RELEVANT_CHUNKS.relevance_score tenían
--      anotaciones de valores permitidos en el propio DER ("dev/test",
--      "0/1"); se tradujeron a CHECK constraints explícitos.
--   6. FLOAT del DER se mapeó a DOUBLE PRECISION (Postgres trata FLOAT como
--      alias de DOUBLE PRECISION sin precisión especificada, así que son
--      equivalentes; se dejó el tipo explícito por claridad).
--   7. Todas las PK de tipo INTEGER autoincremental se implementaron como
--      SERIAL (equivalente a INTEGER + secuencia automática).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- DER1 — CHATBOT
-- ============================================================================

CREATE TABLE roles (
    id           SERIAL PRIMARY KEY,
    role_name    VARCHAR(100) NOT NULL,
    description  TEXT,
    permissions  TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id             SERIAL PRIMARY KEY,
    role_id        INTEGER NOT NULL REFERENCES roles(id),
    username       VARCHAR(100) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(255),
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login     TIMESTAMP
);

-- PK compuesta (id, user_id), tal como está dibujado en el DER — ver
-- Asunción #4 arriba. La columna `id` lleva además UNIQUE (no solo SERIAL)
-- porque CONVERSATIONS.session_id la referencia de forma aislada más abajo.
CREATE TABLE sessions (
    id           SERIAL UNIQUE,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    token_hash   VARCHAR(255) NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at   TIMESTAMP NOT NULL,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (id, user_id)
);

CREATE TABLE experiment_conditions (
    id                    SERIAL PRIMARY KEY,
    embedding_model       VARCHAR(100) NOT NULL,
    retrieval_technique   VARCHAR(100) NOT NULL,
    generative_model      VARCHAR(100) NOT NULL
);

CREATE TABLE conversations (
    id                       SERIAL PRIMARY KEY,
    session_id               INTEGER NOT NULL REFERENCES sessions(id),      -- ver Asunción #3
    user_id                  INTEGER NOT NULL REFERENCES users(id),
    experiment_condition_id  INTEGER NOT NULL REFERENCES experiment_conditions(id),
    title                    VARCHAR(255),
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id               SERIAL PRIMARY KEY,
    conversation_id  INTEGER NOT NULL REFERENCES conversations(id),
    sender_role      VARCHAR(50) NOT NULL,
    content          TEXT NOT NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- DER2 — CORPUS INDEXADO
-- ============================================================================

CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    filename    VARCHAR(255) NOT NULL,
    file_type   VARCHAR(50) NOT NULL,
    file_path   VARCHAR(500) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunk_configs (
    id                   SERIAL PRIMARY KEY,
    name                 VARCHAR(100) NOT NULL,
    chunk_size           INTEGER NOT NULL,
    overlap              INTEGER NOT NULL,
    overlap_percentage   NUMERIC(5,2) NOT NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chunks (
    id                   SERIAL PRIMARY KEY,
    document_id          INTEGER NOT NULL REFERENCES documents(id),
    chunk_config_id      INTEGER NOT NULL REFERENCES chunk_configs(id),
    format               VARCHAR(50),
    chunk_index          INTEGER NOT NULL,
    chunk_text           TEXT NOT NULL,
    start_token_offset   INTEGER NOT NULL,
    end_token_offset     INTEGER NOT NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE embedding_models (
    id           SERIAL PRIMARY KEY,
    model_name   VARCHAR(255) NOT NULL UNIQUE,
    dimensions   INTEGER NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de unión pura: la PK es la combinación (chunk_id, embedding_model_id),
-- consistente con el diseño 2x2 (un embedding por chunk y por modelo).
CREATE TABLE embeddings (
    chunk_id             INTEGER NOT NULL REFERENCES chunks(id),
    embedding_model_id   INTEGER NOT NULL REFERENCES embedding_models(id),
    embedding            VECTOR(768) NOT NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chunk_id, embedding_model_id)
);

-- ============================================================================
-- DER3 — EVALUACIÓN
-- ============================================================================

CREATE TABLE gold_standard_queries (
    id             SERIAL PRIMARY KEY,
    query_text     TEXT NOT NULL,
    language       VARCHAR(10) NOT NULL,          -- p.ej. 'ES' / 'JO'
    annotator      VARCHAR(100),
    category       VARCHAR(100),
    is_validated   BOOLEAN NOT NULL DEFAULT FALSE,
    split          VARCHAR(10) NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_gold_standard_split CHECK (split IN ('dev', 'test'))
);

-- Tabla de unión pura: PK = (query_id, chunk_id).
CREATE TABLE relevant_chunks (
    query_id          INTEGER NOT NULL REFERENCES gold_standard_queries(id),
    chunk_id          INTEGER NOT NULL REFERENCES chunks(id),
    relevance_score   INTEGER NOT NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (query_id, chunk_id),
    CONSTRAINT chk_relevant_chunks_score CHECK (relevance_score IN (0, 1))
);

-- Tabla de unión pura: PK = (query_id, experiment_condition_id, chunk_id) —
-- una fila por chunk recuperado, por consulta, por condición experimental.
CREATE TABLE retrieval_results (
    query_id                 INTEGER NOT NULL REFERENCES gold_standard_queries(id),
    experiment_condition_id  INTEGER NOT NULL REFERENCES experiment_conditions(id),
    chunk_id                 INTEGER NOT NULL REFERENCES chunks(id),
    rank                     INTEGER NOT NULL,
    score                    DOUBLE PRECISION NOT NULL,
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (query_id, experiment_condition_id, chunk_id)
);

-- Tabla de unión pura: PK = (query_id, experiment_condition_id) — una fila
-- de métricas por consulta y por condición (400 filas totales esperadas).
CREATE TABLE evaluation_metrics (
    query_id                 INTEGER NOT NULL REFERENCES gold_standard_queries(id),
    experiment_condition_id  INTEGER NOT NULL REFERENCES experiment_conditions(id),
    mrr                      DOUBLE PRECISION,
    ndcg_at_5                DOUBLE PRECISION,
    recall_at_5              DOUBLE PRECISION,
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (query_id, experiment_condition_id)
);

-- ============================================================================
-- DER1 (continuación) — depende de CHUNKS, definida arriba en DER2
-- ============================================================================

-- Tabla de unión pura: PK = (message_id, chunk_id) — qué chunks sustentaron
-- cada respuesta generada, con su score y posición de ranking.
CREATE TABLE messages_chunks (
    message_id        INTEGER NOT NULL REFERENCES messages(id),
    chunk_id          INTEGER NOT NULL REFERENCES chunks(id),
    relevance_score   DOUBLE PRECISION,
    rank_position     INTEGER,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, chunk_id)
);

-- ============================================================================
-- DER4 — RENDIMIENTO
-- ============================================================================

-- Una fila por experimento (4 filas totales esperadas).
CREATE TABLE performance_metrics (
    id                        SERIAL PRIMARY KEY,
    experiment_condition_id   INTEGER NOT NULL REFERENCES experiment_conditions(id),
    latency_embedding_ms      DOUBLE PRECISION,
    latency_retrieval_ms      DOUBLE PRECISION,
    latency_generation_ms     DOUBLE PRECISION,
    latency_total_ms          DOUBLE PRECISION,
    latency_p95_ms            DOUBLE PRECISION,
    mrr_es                    DOUBLE PRECISION,
    mrr_jo                    DOUBLE PRECISION,
    ndcg_es                   DOUBLE PRECISION,
    ndcg_jo                   DOUBLE PRECISION,
    robustness_ir             DOUBLE PRECISION,   -- = 1 - |mrr_es - mrr_jo|
    created_at                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

-- Índice HNSW para búsqueda por similitud coseno (parámetros confirmados en
-- tu metodología: m=16, ef_construction=64).
--
-- NOTA sobre los "2 índices HNSW parciales" documentados en tu capítulo de
-- Metodología: un índice parcial por embedding_model_id requiere conocer el
-- valor literal del id de cada modelo (ej. WHERE embedding_model_id = 1),
-- y eso recién se sabe después de insertar las filas en EMBEDDING_MODELS.
-- Por eso se deja acá un índice único sobre toda la tabla como punto de
-- partida funcional; una vez cargados nomic-embed-text-v1.5 y
-- multilingual-bert-gn-base-cased en EMBEDDING_MODELS, reemplazalo por los
-- dos índices parciales (ver plantilla comentada más abajo).
CREATE INDEX idx_embeddings_hnsw
    ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Plantilla para los 2 índices parciales (activar después de insertar en
-- EMBEDDING_MODELS y confirmar los ids reales):
--
-- DROP INDEX IF EXISTS idx_embeddings_hnsw;
-- CREATE INDEX idx_embeddings_hnsw_nomic
--     ON embeddings USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64)
--     WHERE embedding_model_id = <id_de_nomic_embed_text_v1_5>;
-- CREATE INDEX idx_embeddings_hnsw_bertgn
--     ON embeddings USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64)
--     WHERE embedding_model_id = <id_de_multilingual_bert_gn>;

-- Índices auxiliares sobre FKs consultadas frecuentemente en las 400 corridas
CREATE INDEX idx_conversations_experiment_condition ON conversations(experiment_condition_id);
CREATE INDEX idx_retrieval_results_condition ON retrieval_results(experiment_condition_id);
CREATE INDEX idx_evaluation_metrics_condition ON evaluation_metrics(experiment_condition_id);
CREATE INDEX idx_gold_standard_queries_split ON gold_standard_queries(split);
CREATE INDEX idx_chunks_document ON chunks(document_id);
