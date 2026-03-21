-- Resize food_embeddings.embedding to 1024 (mxbai-embed-large).
-- Drop old column, truncate, re-add with correct dimension.
TRUNCATE TABLE food_embeddings;
ALTER TABLE food_embeddings DROP COLUMN IF EXISTS embedding;
ALTER TABLE food_embeddings ADD COLUMN embedding VECTOR(1024);
CREATE INDEX food_embeddings_embedding_idx
    ON food_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
