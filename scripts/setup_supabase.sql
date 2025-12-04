-- ARCON Vetting Agent - Supabase Database Setup
-- Run this SQL in your Supabase SQL Editor

-- Step 1: Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create the arcon_regulations table
CREATE TABLE IF NOT EXISTS arcon_regulations (
  id BIGSERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding VECTOR(3072),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Create index for fast vector similarity search
CREATE INDEX IF NOT EXISTS arcon_regulations_embedding_idx 
ON arcon_regulations 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 4: Create function for vector similarity search
CREATE OR REPLACE FUNCTION match_arcon_regulations(
  query_embedding vector(3072),
  match_threshold float DEFAULT 0.1,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    content,
    metadata,
    1 - (arcon_regulations.embedding <=> query_embedding) as similarity
  FROM arcon_regulations
  WHERE 1 - (arcon_regulations.embedding <=> query_embedding) > match_threshold
  ORDER BY arcon_regulations.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Verify setup
SELECT 'Setup complete! You can now run: python scripts/setup_database.py' as status;



