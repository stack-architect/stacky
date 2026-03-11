# Stacky

AI-powered search for Next.js, Vercel, and Supabase documentation.

## Stack

- Embeddings: Supabase AI (gte-small, 384 dimensions)
- Vector DB: Supabase pgvector with HNSW indexing
- LLM: OpenRouter API (openrouter/free)
- Backend: Supabase Edge Functions (Deno/TypeScript)
- Frontend: React (planned)
- Deploy: stacky.stackarchitect.io

## Key Decisions

**Supabase gte-small over all-MiniLM-L6-v2** - Native support in Supabase Edge Runtime, no external dependencies, faster cold starts.

**Supabase Edge Functions over FastAPI** - Serverless, built-in AI inference, eliminates need for separate Python service.

**Config validation** - Added config.json and embedding_metadata table to prevent model mismatches between embedding generation and query-time.

**Comprehensive corpus** - 8,145 chunks from ~2,100 pages across three documentation sources.

**HNSW indexing** - Fast approximate nearest neighbor search optimized for <10k document chunks.

## Key Technical Concepts

**pgvector** - PostgreSQL extension for vector similarity search. Stores embeddings as `VECTOR(384)` type and enables semantic search through vector operations.

**HNSW (Hierarchical Navigable Small World)** - Graph-based indexing algorithm for approximate nearest neighbor search. Provides sub-linear search time with high recall.

**Cosine similarity** - Measures semantic similarity between embeddings (0-1 scale). Implemented via pgvector's `<=>` cosine distance operator where `similarity = 1 - distance`.

**Embeddings (384 dimensions)** - Numerical vector representations of text from gte-small model. Each chunk converted to 384-dimensional vector for semantic comparison.

## Setup

### Prerequisites
- Python 3.9+
- Supabase CLI
- Node.js 18+ (for Edge Functions)

### Installation

```bash
# 1. Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start Supabase locally
supabase start

# 3. Scrape documentation (~2,100 pages, takes ~15 min)
python3 scrapers/scraper.py all

# 4. Chunk documents
python3 scripts/chunk_documents.py

# 5. Generate embeddings and load to database
python3 scripts/generate_embeddings.py

# 6. Serve Edge Functions
supabase functions serve advice,business --env-file supabase/.env.local
```

### Testing

**Stack Advisor** - Get technical/architectural advice:
```bash
curl -X POST http://localhost:54321/functions/v1/advice \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"query": "How should I structure authentication in Next.js with Supabase?"}'
```

**Business Assistant** - Ask about StackArchitect:
```bash
curl -X POST http://localhost:54321/functions/v1/business \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{"query": "What services does StackArchitect offer?"}'
```

### Environment Variables

**Root `.env` file** (for Python scripts):
```bash
cp .env.example .env
```
Configure:
- `SUPABASE_URL` - Local: http://127.0.0.1:54321
- `SUPABASE_SERVICE_KEY` - From `supabase status`
- `OPENROUTER_API_KEY` - Get from https://openrouter.ai/keys

**Supabase `.env.local` file** (for Edge Functions):
```bash
# Create supabase/.env.local
OPENROUTER_API_KEY=your-key-here
```

See [ROADMAP.md](ROADMAP.md) for development plan.
