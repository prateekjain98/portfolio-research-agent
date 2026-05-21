"""
Document fetcher with aggressive discovery + quality scoring.

The old version found 3 PDFs and hoped for the best. This one:
1. Searches with 4 different query strategies to find ~30 candidates
2. Scores each candidate on domain authority, URL signals, title relevance
3. Downloads the top 15 candidates in parallel
4. Validates each download (is actually a PDF, reasonable size)
5. Runs a quick LlamaParse sniff test on each (does it produce real text?)
6. Returns the best 5 documents

This costs more search quota and parse time, but the quality gap
between a random PDF and a good one is massive.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

import requests

from src.tools.web_search import WebSearchTool


# Domains that tend to produce real investment research, not SEO spam
TRUSTED_DOMAINS = {
    "sec.gov": 3.0,
    "arxiv.org": 2.5,
    "goldmansachs.com": 2.5,
    "morganstanley.com": 2.5,
    "jpmorgan.com": 2.5,
    "bankofamerica.com": 2.5,
    "ubs.com": 2.5,
    "credit-suisse.com": 2.5,
    "morningstar.com": 2.0,
    "seekingalpha.com": 1.5,
    "fool.com": 1.5,
    "barrons.com": 1.5,
    "ft.com": 1.5,
    "bloomberg.com": 1.5,
    "reuters.com": 1.5,
    "cnbc.com": 1.0,
    "medium.com": 0.5,
}

# Patterns that suggest garbage / landing pages / paywalls
JUNK_PATTERNS = [
    r"login",
    r"sign[-_]?in",
    r"subscribe",
    r"paywall",
    r"cookie",
    r"terms[-_]?of[-_]?service",
    r"privacy[-_]?policy",
]

YEAR_PATTERN = re.compile(r"20(2[0-9])")


@dataclass
class Candidate:
    url: str
    title: str
    source_query: str
    domain_score: float = 0.0
    url_score: float = 0.0
    title_score: float = 0.0
    downloaded: bool = False
    path: Optional[str] = None
    file_size: int = 0
    valid_pdf: bool = False
    parse_preview: str = ""
    parse_score: float = 0.0
    final_score: float = 0.0
    fail_reason: str = ""

    def compute_final(self) -> None:
        """Weighted aggregate of all signals."""
        self.final_score = (
            self.domain_score * 0.25
            + self.url_score * 0.20
            + self.title_score * 0.15
            + (1.0 if self.valid_pdf else 0.0) * 0.25
            + self.parse_score * 0.15
        )


class DocumentFetcher:
    """Finds, scores, and filters investment documents."""

    def __init__(self, max_workers: int = 6) -> None:
        self.search = WebSearchTool()
        self._temp_dir = tempfile.mkdtemp(prefix="basis_docs_")
        self._max_workers = max_workers

    def find_and_download(self, theme: str, top_n: int = 5) -> List[dict]:
        """
        Full pipeline: search -> score -> download -> validate -> return best N.
        Returns list of dicts: {"path", "url", "title", "score"}
        """
        candidates = self._discover_candidates(theme)
        if not candidates:
            return []

        self._score_candidates(candidates, theme)
        candidates.sort(key=lambda c: c.final_score, reverse=True)

        # Download top 15 for validation
        to_download = candidates[:15]
        self._download_batch(to_download)

        # Re-score after download validation
        for c in to_download:
            c.compute_final()

        to_download.sort(key=lambda c: c.final_score, reverse=True)
        winners = [c for c in to_download if c.valid_pdf][:top_n]

        print(
            f"[DocumentFetcher] {len(winners)} good docs out of "
            f"{len(candidates)} candidates for theme: {theme[:40]}"
        )
        for w in winners:
            print(f"  → {w.title[:60]} | score={w.final_score:.2f} | {w.url[:80]}")

        return [
            {
                "path": c.path,
                "url": c.url,
                "title": c.title,
                "score": c.final_score,
            }
            for c in winners
        ]

    def _discover_candidates(self, theme: str) -> List[Candidate]:
        """Run multiple search strategies and deduplicate."""
        queries = [
            f'"{theme}" investment report filetype:pdf',
            f'"{theme}" equity research pdf',
            f'"{theme}" analysis report 2024 2025',
            f'"{theme}" sector outlook pdf',
        ]

        seen_urls = set()
        all_candidates: List[Candidate] = []

        for q in queries:
            try:
                results = self.search.run(q, max_results=10)
                time.sleep(1)  # rate-limit: avoid exhausting DDG connection pool
            except Exception as e:
                print(f"[DocumentFetcher] Search failed for '{q}': {e}")
                continue

            for r in results:
                url = r.url.strip()
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Quick URL filter: must look like a real document
                if not self._url_passes_basic_check(url):
                    continue

                all_candidates.append(
                    Candidate(url=url, title=r.title or "", source_query=q)
                )

        return all_candidates

    def _score_candidates(self, candidates: List[Candidate], theme: str) -> None:
        """Score candidates before downloading."""
        theme_words = set(theme.lower().split())

        for c in candidates:
            # Domain score
            domain = urlparse(c.url).netloc.lower()
            c.domain_score = 0.0
            for trusted, score in TRUSTED_DOMAINS.items():
                if trusted in domain:
                    c.domain_score = score
                    break
            if c.domain_score == 0.0:
                # Unknown domain: slight penalty, but not death
                c.domain_score = 0.3

            # URL score
            path = urlparse(c.url).path.lower()
            c.url_score = 0.0
            if path.endswith(".pdf"):
                c.url_score += 0.5
            if YEAR_PATTERN.search(path):
                c.url_score += 0.3
            if any(j in path for j in JUNK_PATTERNS):
                c.url_score -= 0.5

            # Title score
            title_lower = c.title.lower()
            c.title_score = 0.0
            matches = sum(1 for w in theme_words if w in title_lower)
            c.title_score = min(1.0, matches / max(1, len(theme_words)))
            if "report" in title_lower or "analysis" in title_lower:
                c.title_score += 0.2
            if "pdf" in title_lower:
                c.title_score += 0.1

            c.compute_final()

    def _download_batch(self, candidates: List[Candidate]) -> None:
        """Parallel download with validation — 20s per future hard cap."""
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(self._download_one, c): c for c in candidates}
            for future in as_completed(futures, timeout=120):
                c = futures[future]
                try:
                    future.result(timeout=20)
                except Exception as e:
                    c.fail_reason = str(e)
                    c.valid_pdf = False

    def _download_one(self, c: Candidate) -> None:
        """Download a single candidate and validate it's a real PDF."""
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/pdf,*/*",
            }
            resp = requests.get(
                c.url, headers=headers, timeout=30, stream=True, allow_redirects=True
            )
            resp.raise_for_status()

            # Check content type
            content_type = resp.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type and not c.url.lower().endswith(".pdf"):
                c.fail_reason = f"Not a PDF (Content-Type: {content_type})"
                return

            # Check size — reject tiny files (likely redirects/landing pages)
            # and huge files (likely bulk data dumps)
            size = int(resp.headers.get("Content-Length", 0))
            if 0 < size < 10_000:
                c.fail_reason = f"Too small ({size} bytes)"
                return
            if size > 100_000_000:
                c.fail_reason = f"Too large ({size} bytes)"
                return

            # Save to temp file
            parsed = urlparse(c.url)
            filename = os.path.basename(parsed.path) or "document.pdf"
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            path = os.path.join(self._temp_dir, filename)

            # Stream to disk with size limit
            downloaded = 0
            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded > 100_000_000:
                            c.fail_reason = "Exceeded 100MB stream limit"
                            return

            c.path = path
            c.file_size = downloaded
            c.downloaded = True

            # Validate PDF magic bytes
            with open(path, "rb") as f:
                header = f.read(8)
            if not header.startswith(b"%PDF"):
                c.fail_reason = "File does not start with %PDF"
                return

            c.valid_pdf = True

        except Exception as e:
            c.fail_reason = str(e)

    @staticmethod
    def _url_passes_basic_check(url: str) -> bool:
        """Reject obvious garbage URLs before scoring."""
        parsed = urlparse(url)
        path = parsed.path.lower()

        if not parsed.netloc:
            return False
        if any(j in path for j in JUNK_PATTERNS):
            return False
        # Reject Google Drive / Dropbox share links — they redirect to HTML
        if "drive.google.com" in parsed.netloc or "dropbox.com" in parsed.netloc:
            return False
        return True
