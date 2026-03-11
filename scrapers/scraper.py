#!/usr/bin/env python3
"""
Unified scraper for all documentation sources.
Usage: python scraper.py [vercel|nextjs|supabase|all] [--test]
"""

import json
import re
import requests
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict
from tempfile import mkdtemp
from time import sleep


class BaseScraper:
    """Base class with common functionality."""

    def __init__(self, output_name: str, output_dir: str = "data/raw"):
        self.output_name = output_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_frontmatter(self, content: str) -> tuple[Dict, str]:
        """Extract YAML frontmatter and return (metadata, content)."""
        frontmatter = {}
        markdown_content = content

        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                markdown_content = parts[2].strip()

                for line in frontmatter_text.strip().split('\n'):
                    if ':' in line and not line.strip().startswith('#'):
                        key, value = line.split(':', 1)
                        frontmatter[key.strip()] = value.strip().strip('"\'')

        return frontmatter, markdown_content

    def extract_title(self, frontmatter: Dict, content: str) -> str:
        """Extract title from frontmatter or first H1."""
        title = frontmatter.get('title', '')
        if not title:
            h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if h1_match:
                title = h1_match.group(1)
        return title

    def save(self, docs: List[Dict]):
        """Save docs to JSON."""
        output_path = self.output_dir / self.output_name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(docs)} documents to {output_path}")


class VercelScraper(BaseScraper):
    """Scraper for Vercel docs using markdown API."""

    BASE_URL = "https://vercel.com"
    HEADERS = {"Accept": "text/markdown"}

    def __init__(self, test: bool = False):
        output_name = "vercel_docs_test.json" if test else "vercel_docs.json"
        super().__init__(output_name)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_sitemap(self) -> List[str]:
        """Fetch sitemap and return all doc URLs."""
        print("Fetching Vercel sitemap...")
        response = self.session.get(f"{self.BASE_URL}/docs/sitemap.md")

        if response.status_code != 200:
            raise Exception(f"Failed to fetch sitemap: {response.status_code}")

        urls = re.findall(r'\[.*?\]\((/docs/[^\)]+)\)', response.text)
        urls = list(set(urls))
        print(f"Found {len(urls)} pages")
        return urls

    def fetch_page(self, url: str) -> Dict:
        """Fetch and parse a single page."""
        response = self.session.get(f"{self.BASE_URL}{url}")

        if response.status_code != 200:
            print(f"Warning: Failed to fetch {url}: {response.status_code}")
            return None

        frontmatter, content = self.parse_frontmatter(response.text)
        title = self.extract_title(frontmatter, content)

        return {
            'url': url,
            'title': title,
            'content': content,
            'metadata': frontmatter
        }

    def scrape(self, limit: int = None) -> List[Dict]:
        """Scrape all Vercel docs."""
        urls = self.fetch_sitemap()

        if limit:
            urls = urls[:limit]
            print(f"Limiting to {limit} pages (test mode)")

        docs = []
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url}")
            doc = self.fetch_page(url)
            if doc:
                docs.append(doc)
            sleep(0.5)

        return docs


class GitHubScraper(BaseScraper):
    """Scraper for GitHub-hosted docs using sparse-checkout."""

    def __init__(self, owner: str, repo: str, docs_path: str, output_name: str):
        super().__init__(output_name)
        self.owner = owner
        self.repo = repo
        self.docs_path = docs_path
        self.repo_url = f"https://github.com/{owner}/{repo}"

    def clone_docs(self) -> Path:
        """Clone only docs directory."""
        print(f"Cloning {self.owner}/{self.repo} (docs only)...")
        temp_dir = Path(mkdtemp())
        repo_dir = temp_dir / self.repo

        try:
            subprocess.run(
                ["git", "clone", "--filter=blob:none", "--sparse", self.repo_url],
                cwd=temp_dir,
                check=True,
                capture_output=True
            )

            subprocess.run(
                ["git", "sparse-checkout", "set", self.docs_path],
                cwd=repo_dir,
                check=True,
                capture_output=True
            )

            print(f"Cloned {self.docs_path}")
            return repo_dir / self.docs_path

        except subprocess.CalledProcessError as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Failed to clone: {e}")

    def scrape(self, limit: int = None) -> List[Dict]:
        """Scrape docs from GitHub."""
        docs_dir = self.clone_docs()
        temp_root = docs_dir.parent.parent

        try:
            files = list(docs_dir.glob("**/*.md")) + list(docs_dir.glob("**/*.mdx"))
            print(f"Found {len(files)} markdown files")

            if limit:
                files = files[:limit]
                print(f"Limiting to {limit} files (test mode)")

            docs = []
            for i, file_path in enumerate(files, 1):
                print(f"[{i}/{len(files)}] {file_path.name}")

                try:
                    content = file_path.read_text(encoding='utf-8')
                    frontmatter, markdown = self.parse_frontmatter(content)
                    title = self.extract_title(frontmatter, markdown)

                    docs.append({
                        'path': str(file_path.relative_to(docs_dir)),
                        'title': title,
                        'content': markdown,
                        'metadata': frontmatter
                    })
                except Exception as e:
                    print(f"Warning: Failed to read {file_path}: {e}")

            return docs

        finally:
            print("Cleaning up...")
            shutil.rmtree(temp_root, ignore_errors=True)


def scrape_vercel(test: bool = False):
    """Scrape Vercel documentation."""
    print("=== Vercel Documentation ===\n")
    scraper = VercelScraper(test=test)
    docs = scraper.scrape(limit=5 if test else None)
    scraper.save(docs)
    print(f"✓ Vercel: {len(docs)} documents\n")


def scrape_nextjs(test: bool = False):
    """Scrape Next.js documentation."""
    print("=== Next.js Documentation ===\n")
    output_name = "nextjs_docs_test.json" if test else "nextjs_docs.json"
    scraper = GitHubScraper("vercel", "next.js", "docs", output_name)
    docs = scraper.scrape(limit=5 if test else None)
    scraper.save(docs)
    print(f"✓ Next.js: {len(docs)} documents\n")


def scrape_supabase(test: bool = False):
    """Scrape Supabase documentation."""
    print("=== Supabase Documentation ===\n")
    output_name = "supabase_docs_test.json" if test else "supabase_docs.json"
    scraper = GitHubScraper("supabase", "supabase", "apps/docs", output_name)
    docs = scraper.scrape(limit=5 if test else None)
    scraper.save(docs)
    print(f"✓ Supabase: {len(docs)} documents\n")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scraper.py [vercel|nextjs|supabase|all] [--test]")
        sys.exit(1)

    target = sys.argv[1]
    test_mode = '--test' in sys.argv

    if test_mode:
        print("TEST MODE: Scraping 5 files from each source\n")

    if target == 'vercel':
        scrape_vercel(test=test_mode)
    elif target == 'nextjs':
        scrape_nextjs(test=test_mode)
    elif target == 'supabase':
        scrape_supabase(test=test_mode)
    elif target == 'all':
        scrape_vercel(test=test_mode)
        scrape_nextjs(test=test_mode)
        scrape_supabase(test=test_mode)
        print("✓ All documentation scraped successfully")
    else:
        print(f"Unknown target: {target}")
        print("Use: vercel, nextjs, supabase, or all")
        sys.exit(1)


if __name__ == "__main__":
    main()
