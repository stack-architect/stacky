-- =====================================================
-- Stacky RAG System - Initial Database Setup
-- =====================================================
-- This migration sets up the complete vector search infrastructure
-- for the Stacky documentation search system.
--
-- Components:
-- 1. pgvector extension for vector similarity search
-- 2. document_chunks table with embeddings
-- 3. embedding_metadata table for model consistency
-- 4. match_documents function for vector search
-- 5. Constraints and indexes for data integrity

-- =====================================================
-- 1. Enable pgvector extension
-- =====================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- 2. Document chunks table with embeddings
-- =====================================================
CREATE TABLE document_chunks (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(384) NOT NULL,
  model_version TEXT DEFAULT 'gte-small-v1' NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Add constraint to enforce embedding dimensions
ALTER TABLE document_chunks
ADD CONSTRAINT check_embedding_dimensions
CHECK (vector_dims(embedding) = 384);

-- Create HNSW index for fast vector similarity search
-- Using cosine distance for semantic similarity
CREATE INDEX idx_document_chunks_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Index on source for filtering
CREATE INDEX idx_document_chunks_source ON document_chunks(source);

-- Enable Row Level Security
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read
CREATE POLICY "Authenticated read access"
  ON document_chunks FOR SELECT
  TO authenticated
  USING (true);

-- Allow service role to insert/update/delete
CREATE POLICY "Service role full access"
  ON document_chunks FOR ALL
  TO service_role
  USING (true);

-- =====================================================
-- 3. Embedding metadata table
-- =====================================================
-- Stores model configuration for consistency validation
-- Only one row allowed to ensure single source of truth
CREATE TABLE embedding_metadata (
  id INTEGER PRIMARY KEY DEFAULT 1,
  model_name TEXT NOT NULL,
  model_python TEXT NOT NULL,
  model_js TEXT NOT NULL,
  dimensions INTEGER NOT NULL,
  total_chunks INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  CONSTRAINT single_row CHECK (id = 1)
);

-- Comment on the constraint
COMMENT ON CONSTRAINT single_row ON embedding_metadata IS
'Ensures only one metadata row exists - the current model configuration';

-- Function to get current embedding config
CREATE OR REPLACE FUNCTION get_embedding_config()
RETURNS TABLE (
  model_name TEXT,
  model_python TEXT,
  model_js TEXT,
  dimensions INTEGER,
  total_chunks INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    em.model_name,
    em.model_python,
    em.model_js,
    em.dimensions,
    em.total_chunks
  FROM embedding_metadata em
  WHERE em.id = 1;
END;
$$;

-- =====================================================
-- 4. Vector search function
-- =====================================================
-- Searches for documents similar to the query embedding
-- Returns top N matches ordered by cosine similarity
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding VECTOR(384),
  match_count INTEGER DEFAULT 5
)
RETURNS TABLE (
  id BIGINT,
  source TEXT,
  url TEXT,
  title TEXT,
  content TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    document_chunks.id,
    document_chunks.source,
    document_chunks.url,
    document_chunks.title,
    document_chunks.content,
    1 - (document_chunks.embedding <=> query_embedding) AS similarity
  FROM document_chunks
  WHERE document_chunks.embedding IS NOT NULL
  ORDER BY document_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Add helpful comments
COMMENT ON TABLE document_chunks IS
'Stores documentation chunks with their vector embeddings for semantic search';

COMMENT ON TABLE embedding_metadata IS
'Tracks the embedding model configuration to ensure consistency between generation and query time';

COMMENT ON FUNCTION match_documents IS
'Performs vector similarity search using cosine distance to find relevant documentation chunks';
