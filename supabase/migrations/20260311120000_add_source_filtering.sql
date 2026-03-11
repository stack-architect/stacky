-- Update match_documents function to support optional source filtering
-- Replaces the existing function with backward-compatible version

-- Drop old function first
DROP FUNCTION IF EXISTS match_documents(VECTOR(384), INTEGER);

-- Create new function with source filtering
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding VECTOR(384),
  match_count INTEGER DEFAULT 5,
  filter_source TEXT DEFAULT NULL
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
    AND (filter_source IS NULL OR document_chunks.source = filter_source)
  ORDER BY document_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_documents(VECTOR(384), INTEGER, TEXT) IS
'Performs vector similarity search using cosine distance. Optional filter_source parameter restricts results to a specific documentation source (e.g., "stackarchitect").';
