"""
Chunk documentation into 400-600 token pieces for embedding generation.
"""
import json
import tiktoken
from pathlib import Path
from typing import List, Dict


def chunk_text(text: str, min_tokens: int = 400, max_tokens: int = 600) -> List[str]:
    """
    Split text into chunks of 400-600 tokens, preserving semantic boundaries.
    Uses cl100k_base encoding (GPT-4/ChatGPT tokenizer).
    """
    enc = tiktoken.get_encoding("cl100k_base")

    # Split on double newlines (paragraphs) and headings
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(enc.encode(para))

        # If single paragraph exceeds max_tokens, split it
        if para_tokens > max_tokens:
            # Flush current chunk if exists
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_tokens = 0

            # Split long paragraph by sentences
            sentences = para.split('. ')
            for sent in sentences:
                sent_tokens = len(enc.encode(sent))
                if current_tokens + sent_tokens > max_tokens and current_chunk:
                    chunks.append('. '.join(current_chunk) + '.')
                    current_chunk = [sent]
                    current_tokens = sent_tokens
                else:
                    current_chunk.append(sent)
                    current_tokens += sent_tokens

            if current_chunk:
                chunks.append('. '.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            continue

        # Check if adding this paragraph exceeds max_tokens
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens

        # Flush if we're in the target range
        if current_tokens >= min_tokens:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = []
            current_tokens = 0

    # Add remaining content
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def process_documents(input_file: Path, source: str) -> List[Dict]:
    """Process a single JSON file and return chunked documents."""
    with open(input_file) as f:
        docs = json.load(f)

    chunked_docs = []

    for doc in docs:
        content = doc.get('content', '')
        if not content:
            continue

        chunks = chunk_text(content)

        # Handle different JSON structures
        # Vercel: uses 'url' and 'full_url'
        # Next.js/Supabase: use 'path'
        url = doc.get('full_url') or doc.get('url') or doc.get('path', '')

        # Construct full URL for Next.js/Supabase/StackArchitect if needed
        if url and not url.startswith('http'):
            if source == 'nextjs':
                url = f'https://nextjs.org/docs{url}'
            elif source == 'supabase':
                url = f'https://supabase.com/docs{url}'
            elif source == 'stackarchitect':
                url = f'https://stackarchitect.io{url}'

        for i, chunk in enumerate(chunks):
            chunked_docs.append({
                'source': source,
                'url': url,
                'title': doc.get('title', ''),
                'content': chunk,
                'chunk_index': i
            })

    return chunked_docs


def main():
    """Process all documentation files and output chunks."""
    data_dir = Path('data/raw')
    output_file = Path('data/chunks.json')

    all_chunks = []

    # Process each source
    for source_file, source_name in [
        ('vercel_docs.json', 'vercel'),
        ('nextjs_docs.json', 'nextjs'),
        ('supabase_docs.json', 'supabase'),
        ('stackarchitect_docs.json', 'stackarchitect')
    ]:
        file_path = data_dir / source_file
        if file_path.exists():
            print(f"Processing {source_name}...")
            chunks = process_documents(file_path, source_name)
            all_chunks.extend(chunks)
            print(f"  Generated {len(chunks)} chunks")

    # Save chunks
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Saved to: {output_file}")


if __name__ == '__main__':
    main()
