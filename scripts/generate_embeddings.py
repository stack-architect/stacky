#!/usr/bin/env python3
"""
Generate embeddings for document chunks and load to Supabase pgvector.
Uses Supabase/gte-small model (384 dimensions).
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client

# Load environment variables from .env file
load_dotenv()

def load_config():
    """Load configuration from config.json."""
    config_path = Path(__file__).parent.parent / 'config.json'
    with open(config_path, 'r') as f:
        return json.load(f)

def load_chunks(chunks_path: str) -> list:
    """Load chunks from JSON file."""
    with open(chunks_path, 'r') as f:
        return json.load(f)

def generate_embeddings(model, chunks: list, batch_size: int = 32, model_name: str = "gte-small") -> list:
    """Generate embeddings for chunks in batches."""
    print(f"\nGenerating embeddings for {len(chunks)} chunks...")
    print(f"Model: {model_name} (384 dimensions)")
    print(f"Batch size: {batch_size}\n")

    embeddings = []
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk['content'] for chunk in batch]
        batch_embeddings = model.encode(texts, show_progress_bar=False)
        embeddings.extend(batch_embeddings)

        progress = min(i + batch_size, total)
        print(f"  Progress: {progress}/{total} ({progress/total*100:.1f}%)", end='\r')

    print(f"\n  ✓ Generated {len(embeddings)} embeddings\n")
    return embeddings

def insert_to_supabase(supabase, chunks: list, embeddings: list, batch_size: int = 100):
    """Insert chunks with embeddings to Supabase in batches."""
    print(f"Inserting to Supabase...")
    print(f"Insert batch size: {batch_size}\n")

    total = len(chunks)
    inserted = 0

    for i in range(0, total, batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size]

        rows = []
        for chunk, embedding in zip(batch_chunks, batch_embeddings):
            rows.append({
                'source': chunk['source'],
                'url': chunk['url'],
                'title': chunk['title'],
                'content': chunk['content'],
                'embedding': embedding.tolist(),
                'model_version': 'gte-small-v1'
            })

        supabase.table('document_chunks').insert(rows).execute()
        inserted += len(rows)
        print(f"  Progress: {inserted}/{total} ({inserted/total*100:.1f}%)", end='\r')

    print(f"\n  ✓ Inserted {inserted} rows\n")

def store_metadata(supabase, config: dict, total_chunks: int):
    """Store embedding metadata in database for validation."""
    print("Storing embedding metadata...")
    embedding_config = config['embedding']

    metadata = {
        'id': 1,  # Single row constraint
        'model_name': embedding_config['model'],
        'model_python': embedding_config['model_python'],
        'model_js': embedding_config['model_js'],
        'dimensions': embedding_config['dimensions'],
        'total_chunks': total_chunks
    }

    # Upsert to handle re-runs
    supabase.table('embedding_metadata').upsert(metadata).execute()
    print("  ✓ Metadata stored\n")

def main():
    # Load configuration
    config = load_config()
    embedding_config = config['embedding']

    # Paths and environment
    project_root = Path(__file__).parent.parent
    chunks_path = project_root / 'data' / 'chunks.json'

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")

    # Load model from config
    print("Loading sentence-transformers model...")
    print(f"  Model: {embedding_config['model_python']}")
    print(f"  Expected dimensions: {embedding_config['dimensions']}")
    model = SentenceTransformer(embedding_config['model_python'])
    print("  ✓ Model loaded\n")

    # Load chunks
    print("Loading chunks...")
    chunks = load_chunks(chunks_path)
    print(f"  ✓ Loaded {len(chunks)} chunks\n")

    # Generate embeddings
    embeddings = generate_embeddings(
        model,
        chunks,
        batch_size=embedding_config['batch_size'],
        model_name=embedding_config['model']
    )

    # Verify dimensions match config
    actual_dims = embeddings[0].shape[0]
    expected_dims = embedding_config['dimensions']
    if actual_dims != expected_dims:
        raise ValueError(f"Dimension mismatch! Expected {expected_dims}, got {actual_dims}")
    print(f"  ✓ Verified embedding dimensions: {actual_dims}\n")

    # Connect to Supabase
    print("Connecting to Supabase...")
    supabase = create_client(supabase_url, supabase_key)
    print("  ✓ Connected\n")

    # Insert to database
    insert_to_supabase(supabase, chunks, embeddings, batch_size=100)

    # Store metadata for validation
    store_metadata(supabase, config, len(chunks))

    print("=" * 50)
    print("✓ Complete!")
    print(f"  Total chunks processed: {len(chunks)}")
    print(f"  Model: {embedding_config['model']}")
    print(f"  Vector dimensions: {embedding_config['dimensions']}")
    print(f"  Index: HNSW (cosine similarity)")
    print("=" * 50)

if __name__ == '__main__':
    main()
