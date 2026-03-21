-- Resize embedding column from 1536 (OpenAI) to 768 (nomic-embed-text)
-- Safe to run on an empty food_embeddings table.
DROP INDEX IF EXISTS food_embeddings_embedding_idx;

ALTER TABLE food_embeddings DROP COLUMN embedding;
ALTER TABLE food_embeddings ADD COLUMN embedding VECTOR(768) NOT NULL;

CREATE INDEX food_embeddings_embedding_idx
    ON food_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
