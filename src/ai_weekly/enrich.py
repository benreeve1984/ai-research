"""Paper enrichment with SemanticScholar and GitHub data."""

import logging
import re
import time
from typing import List, Optional
import requests  # type: ignore
from .harvest import Paper


logger = logging.getLogger(__name__)


class SemanticScholarEnricher:
    """Enriches papers with SemanticScholar data."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-KEY": api_key})

    def enrich_paper(self, paper: Paper) -> Paper:
        """Enrich a single paper with SemanticScholar data."""
        try:
            # Try to find paper by arXiv ID first
            s2_paper = None
            if paper.source == "arxiv":
                arxiv_id = paper.id
                s2_paper = self._search_by_arxiv_id(arxiv_id)

            # Fallback to title search
            if not s2_paper:
                s2_paper = self._search_by_title(paper.title)

            if s2_paper:
                paper.citation_count = s2_paper.get("citationCount", 0)

                # Get SPECTER2 embedding if available
                paper_id = s2_paper.get("paperId")
                if paper_id:
                    embedding = self._get_embedding(paper_id)
                    if embedding:
                        paper.specter2_embedding = embedding

                logger.debug(
                    f"Enriched paper {paper.title[:50]}... with {paper.citation_count} citations"
                )
            else:
                paper.citation_count = 0
                logger.debug(
                    f"Could not find paper in SemanticScholar: {paper.title[:50]}..."
                )

        except Exception as e:
            logger.error(f"Error enriching paper with SemanticScholar: {e}")
            paper.citation_count = 0

        # Rate limiting
        time.sleep(0.1)
        return paper

    def _search_by_arxiv_id(self, arxiv_id: str) -> Optional[dict]:
        """Search for paper by arXiv ID."""
        try:
            url = f"{self.BASE_URL}/paper/arXiv:{arxiv_id}"
            params = {"fields": "paperId,title,citationCount"}

            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.debug(f"ArXiv search failed for {arxiv_id}: {e}")

        return None

    def _search_by_title(self, title: str) -> Optional[dict]:
        """Search for paper by title."""
        try:
            url = f"{self.BASE_URL}/paper/search"
            params = {
                "query": title,
                "limit": 1,
                "fields": "paperId,title,citationCount",
            }

            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                if papers:
                    # Check if title is similar enough
                    found_paper = papers[0]
                    if self._titles_similar(title, found_paper.get("title", "")):
                        return found_paper

        except Exception as e:
            logger.debug(f"Title search failed for '{title}': {e}")

        return None

    def _get_embedding(self, paper_id: str) -> Optional[List[float]]:
        """Get SPECTER2 embedding for a paper."""
        if not paper_id:
            return None

        try:
            url = f"{self.BASE_URL}/paper/{paper_id}/embedding"
            params = {"model": "specter2"}

            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")

        except Exception as e:
            logger.debug(f"Embedding fetch failed for {paper_id}: {e}")

        return None

    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar enough (simple character overlap)."""
        title1_clean = re.sub(r"[^\w\s]", "", title1.lower())
        title2_clean = re.sub(r"[^\w\s]", "", title2.lower())

        words1 = set(title1_clean.split())
        words2 = set(title2_clean.split())

        if not words1 or not words2:
            return False

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        jaccard = intersection / union if union > 0 else 0
        return jaccard >= threshold


class GitHubEnricher:
    """Enriches papers with GitHub repository data."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})

    def enrich_paper(self, paper: Paper) -> Paper:
        """Enrich a single paper with GitHub data."""
        if not paper.github_url:
            # Try to find GitHub URL in abstract or title
            github_url = self._extract_github_url(paper.abstract + " " + paper.title)
            if github_url:
                paper.github_url = github_url

        if paper.github_url:
            try:
                stars = self._get_repo_stars(paper.github_url)
                paper.github_stars = stars
                logger.debug(f"Paper {paper.title[:50]}... has {stars} GitHub stars")

            except Exception as e:
                logger.error(f"Error getting GitHub stars: {e}")
                paper.github_stars = 0
        else:
            paper.github_stars = 0

        # Rate limiting
        time.sleep(0.1)
        return paper

    def _extract_github_url(self, text: str) -> Optional[str]:
        """Extract GitHub repository URL from text."""
        # Common GitHub URL patterns
        patterns = [
            r"https?://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+",
            r"github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                url = matches[0]
                if not url.startswith("http"):
                    url = "https://" + url
                return url

        return None

    def _get_repo_stars(self, github_url: str) -> int:
        """Get star count for a GitHub repository."""
        # Extract owner and repo from URL
        match = re.search(r"github\.com/([^/]+)/([^/]+)", github_url)
        if not match:
            return 0

        owner, repo = match.groups()
        # Remove .git suffix if present
        repo = repo.replace(".git", "")

        try:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("stargazers_count", 0)
            elif response.status_code == 404:
                logger.debug(f"Repository not found: {owner}/{repo}")
                return 0
            else:
                logger.warning(
                    f"GitHub API returned {response.status_code} for {owner}/{repo}"
                )
                return 0

        except Exception as e:
            logger.error(f"Error fetching GitHub stars for {owner}/{repo}: {e}")
            return 0


def enrich_papers(
    papers: List[Paper],
    semantic_scholar_api_key: Optional[str] = None,
    github_token: Optional[str] = None,
) -> List[Paper]:
    """Enrich papers with external data."""
    logger.info(f"Enriching {len(papers)} papers with external data")

    # Initialize enrichers
    s2_enricher = SemanticScholarEnricher(semantic_scholar_api_key)
    gh_enricher = GitHubEnricher(github_token)

    enriched_papers = []

    for i, paper in enumerate(papers):
        logger.debug(f"Enriching paper {i+1}/{len(papers)}: {paper.title[:50]}...")

        # Enrich with SemanticScholar data
        paper = s2_enricher.enrich_paper(paper)

        # Enrich with GitHub data
        paper = gh_enricher.enrich_paper(paper)

        enriched_papers.append(paper)

    logger.info("Paper enrichment completed")
    return enriched_papers
