-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Food embeddings: one row per food per model
CREATE TABLE IF NOT EXISTS food_embeddings (
    id         SERIAL PRIMARY KEY,
    food_id    INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    text       TEXT    NOT NULL,
    embedding  VECTOR(1536) NOT NULL,
    model      TEXT    NOT NULL DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (food_id, model)
);

-- IVFFlat index for fast approximate cosine-similarity search
-- Rebuild with higher lists= after loading more data (rule of thumb: sqrt(rows))
CREATE INDEX IF NOT EXISTS food_embeddings_embedding_idx
    ON food_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
