\echo '=== 1) Chunks vs embeddings por modelo (deben coincidir) ==='
SELECT m.model_name,
       (SELECT count(*) FROM chunks) AS chunks,
       count(e.chunk_id)             AS embeddings
FROM embedding_models m
LEFT JOIN embeddings e ON e.embedding_model_id = m.id
GROUP BY m.id, m.model_name
ORDER BY m.id;

\echo '=== 2) Pares (chunk, modelo) sin embedding (debe dar 0) ==='
SELECT count(*) AS faltantes
FROM chunks c
CROSS JOIN embedding_models m
WHERE NOT EXISTS (
    SELECT 1 FROM embeddings e
    WHERE e.chunk_id = c.id AND e.embedding_model_id = m.id
);

\echo '=== 3) Duplicados de (chunk_id, embedding_model_id) (debe dar 0 filas) ==='
SELECT chunk_id, embedding_model_id, count(*) AS repeticiones
FROM embeddings
GROUP BY chunk_id, embedding_model_id
HAVING count(*) > 1;

\echo '=== 4) Restricción de unicidad en la tabla (debe existir la PK compuesta) ==='
SELECT conname, pg_get_constraintdef(oid) AS definicion
FROM pg_constraint
WHERE conrelid = 'embeddings'::regclass AND contype = 'p';

\echo '=== 5) Dimensiones de los vectores por modelo (todas 768) ==='
SELECT embedding_model_id, vector_dims(embedding) AS dimensiones, count(*) AS cantidad
FROM embeddings
GROUP BY embedding_model_id, vector_dims(embedding)
ORDER BY embedding_model_id;

\echo '=== 6) Vectores nulos o de norma cero (debe dar 0) ==='
SELECT count(*) AS vectores_degenerados
FROM embeddings
WHERE embedding IS NULL OR vector_norm(embedding) = 0;

\echo '=== 7) Chunks sin documento y documentos sin chunks (deben dar 0 y 0) ==='
SELECT
  (SELECT count(*) FROM chunks c
     WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = c.document_id)) AS chunks_huerfanos,
  (SELECT count(*) FROM documents d
     WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.document_id = d.id)) AS documentos_sin_chunks;