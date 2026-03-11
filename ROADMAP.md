# Roadmap

## Phase 1: Documentation Collection ✅
- Scraped 2,096 pages (931 Vercel, 383 Next.js, 782 Supabase)
- Unified scraper: Vercel markdown API + GitHub sparse-checkout (rate limit avoidance)
- Raw markdown stored in data/raw/ directory

## Phase 2: Document Processing ✅
- Chunked documents (400-600 tokens, tiktoken tokenizer)
  - Generated 8,145 chunks total
  - Vercel: 4,002 chunks
  - Next.js: 1,461 chunks
  - Supabase: 2,682 chunks
- Generated embeddings (Supabase/gte-small, 384 dimensions)
  - Vector embeddings: Numerical representations of text for semantic search
  - 384 dimensions: Output size from gte-small model
- Loaded to Supabase pgvector with HNSW indexing
  - pgvector: PostgreSQL extension for vector similarity search
  - HNSW: Hierarchical Navigable Small World (graph-based ANN index)
- Added config.json for model consistency validation
- Added embedding_metadata table to track model versions

## Phase 3: Backend API ✅
- Supabase Edge Function for RAG endpoint (/ask)
- Supabase AI inference for embeddings (gte-small model)
- OpenRouter LLM integration (openrouter/free - rotates between free models)
- Cosine similarity search via pgvector with source attribution
  - Cosine similarity: Measures angle between vectors (0-1 scale)
  - pgvector operator: `<=>` for cosine distance, `1 - distance = similarity`
- Config validation to prevent model mismatches

## Phase 4: Frontend ⏳
- React question-answering interface (Vite build)
- Display ranked results with source links + AI-generated answers
- Deploy to stacky.stackarchitect.io (Vercel)

## Phase 5: Evaluation ⏳
- Test query set (~20 questions covering common use cases)
- Retrieval accuracy: precision@5, relevance scoring (target: 85%+)
- End-to-end latency measurement (target: <2s)
- Cost tracking: OpenRouter API usage (target: <$1/month)
