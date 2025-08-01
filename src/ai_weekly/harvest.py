"""Paper harvesting from arXiv and PapersWithCode."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import feedparser
import requests  # type: ignore
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Represents an academic paper."""

    id: str
    title: str
    authors: List[str]
    abstract: str
    published_date: datetime
    url: str
    source: str  # "arxiv" or "paperswithcode"
    categories: List[str]

    # To be filled by enrichment
    citation_count: Optional[int] = None
    github_url: Optional[str] = None
    github_stars: Optional[int] = None
    specter2_embedding: Optional[List[float]] = None

    # To be filled by ranking
    score: Optional[float] = None

    # To be filled by summarization
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["published_date"] = self.published_date.isoformat()
        return data


class ArxivHarvester:
    """Harvests papers from arXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, categories: List[str], days_back: int = 7):
        self.categories = categories
        self.days_back = days_back

    def harvest(self) -> List[Paper]:
        """Harvest papers from arXiv submitted in the last N days."""
        cutoff_date = datetime.now() - timedelta(days=self.days_back)
        papers = []

        for category in self.categories:
            logger.info(f"Harvesting arXiv papers from category: {category}")
            category_papers = self._fetch_category_papers(category, cutoff_date)
            papers.extend(category_papers)

        logger.info(f"Harvested {len(papers)} papers from arXiv")
        return papers

    def _fetch_category_papers(
        self, category: str, cutoff_date: datetime
    ) -> List[Paper]:
        """Fetch papers for a specific category."""
        # arXiv API query parameters
        query = f"cat:{category}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": 100,  # Adjust based on needs
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            papers = []

            for entry in feed.entries:
                # Parse submission date
                try:
                    published_date = datetime.strptime(
                        entry.published, "%Y-%m-%dT%H:%M:%SZ"
                    )
                except ValueError:
                    # Try alternative format
                    published_date = datetime.strptime(
                        entry.published[:19], "%Y-%m-%dT%H:%M:%S"
                    )

                # Skip papers older than cutoff
                if published_date < cutoff_date:
                    continue

                # Extract paper ID from URL
                paper_id = entry.id.split("/abs/")[-1]

                # Parse authors
                authors = (
                    [author.name for author in entry.authors]
                    if hasattr(entry, "authors")
                    else []
                )

                # Parse categories
                categories = []
                if hasattr(entry, "arxiv_primary_category"):
                    categories.append(entry.arxiv_primary_category["term"])
                if hasattr(entry, "tags"):
                    categories.extend([tag["term"] for tag in entry.tags])

                paper = Paper(
                    id=paper_id,
                    title=entry.title.replace("\n", " ").strip(),
                    authors=authors,
                    abstract=entry.summary.replace("\n", " ").strip(),
                    published_date=published_date,
                    url=entry.link,
                    source="arxiv",
                    categories=categories,
                )

                papers.append(paper)

            return papers

        except Exception as e:
            logger.error(f"Error fetching papers from arXiv category {category}: {e}")
            return []


class PapersWithCodeHarvester:
    """Harvests trending papers from PapersWithCode."""

    BASE_URL = "https://paperswithcode.com/api/v1"

    def __init__(self, days_back: int = 7):
        self.days_back = days_back

    def harvest(self) -> List[Paper]:
        """Harvest trending papers from PapersWithCode."""
        logger.info("Harvesting trending papers from PapersWithCode")

        try:
            # Get trending papers
            url = f"{self.BASE_URL}/papers/"
            params = {
                "ordering": "-github_mentions",  # Sort by GitHub activity
                "page_size": 50,  # Limit results
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            papers = []

            cutoff_date = datetime.now() - timedelta(days=self.days_back)

            for item in data.get("results", []):
                # Parse paper data
                paper_date_str = item.get("published")
                if not paper_date_str:
                    continue

                try:
                    paper_date = datetime.fromisoformat(
                        paper_date_str.replace("Z", "+00:00")
                    )
                    paper_date = paper_date.replace(
                        tzinfo=None
                    )  # Remove timezone for consistency
                except ValueError:
                    continue

                # Skip old papers
                if paper_date < cutoff_date:
                    continue

                # Extract GitHub URL if available
                github_url = None
                if item.get("github_url"):
                    github_url = item["github_url"]

                paper = Paper(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    authors=item.get("authors", []),
                    abstract=item.get("abstract", ""),
                    published_date=paper_date,
                    url=item.get("url_abs", ""),
                    source="paperswithcode",
                    categories=[],
                    github_url=github_url,
                )

                papers.append(paper)

            logger.info(f"Harvested {len(papers)} papers from PapersWithCode")
            return papers

        except Exception as e:
            logger.error(f"Error fetching papers from PapersWithCode: {e}")
            return []


def harvest_papers(categories: List[str], days_back: int = 7) -> List[Paper]:
    """Main function to harvest papers from all sources."""
    all_papers = []

    # Harvest from arXiv
    arxiv_harvester = ArxivHarvester(categories, days_back)
    arxiv_papers = arxiv_harvester.harvest()
    all_papers.extend(arxiv_papers)

    # Harvest from PapersWithCode
    pwc_harvester = PapersWithCodeHarvester(days_back)
    pwc_papers = pwc_harvester.harvest()
    all_papers.extend(pwc_papers)

    # Remove duplicates based on title similarity (simple approach)
    unique_papers = []
    seen_titles = set()

    for paper in all_papers:
        title_normalized = paper.title.lower().strip()
        if title_normalized not in seen_titles:
            seen_titles.add(title_normalized)
            unique_papers.append(paper)

    logger.info(f"Total unique papers harvested: {len(unique_papers)}")
    return unique_papers
