-- Reemplaza el índice HNSW único por dos índices parciales, uno por modelo
-- de embeddings (parámetros de la metodología: m=16, ef_construction=64).
-- Lee los ids reales desde embedding_models, así no hay que escribirlos a mano.
DO $$
DECLARE
    nomic_id INTEGER;
    bert_id  INTEGER;
BEGIN
    SELECT id INTO STRICT nomic_id FROM embedding_models
        WHERE model_name = 'nomic-embed-text-v1.5';
    SELECT id INTO STRICT bert_id FROM embedding_models
        WHERE model_name = 'mmaguero/multilingual-bert-gn-base-cased';

    DROP INDEX IF EXISTS idx_embeddings_hnsw;

    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw_nomic '
        'ON embeddings USING hnsw (embedding vector_cosine_ops) '
        'WITH (m = 16, ef_construction = 64) '
        'WHERE embedding_model_id = %s', nomic_id);

    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw_bertgn '
        'ON embeddings USING hnsw (embedding vector_cosine_ops) '
        'WITH (m = 16, ef_construction = 64) '
        'WHERE embedding_model_id = %s', bert_id);
END $$;

