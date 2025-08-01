"""Tests for paper harvesting functionality."""

import pytest
import responses
from datetime import datetime, timedelta
from src.ai_weekly.harvest import (
    ArxivHarvester,
    PapersWithCodeHarvester,
    harvest_papers,
    Paper,
)


class TestArxivHarvester:
    """Test arXiv paper harvesting."""

    @responses.activate
    def test_fetch_category_papers(self):
        """Test fetching papers from a single arXiv category."""
        # Mock arXiv API response
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2024.01001v1</id>
    <updated>2024-01-15T12:00:00Z</updated>
    <published>2024-01-15T12:00:00Z</published>
    <title>Test Paper Title</title>
    <summary>This is a test abstract for the paper.</summary>
    <author>
      <name>John Doe</name>
    </author>
    <author>
      <name>Jane Smith</name>
    </author>
    <link href="http://arxiv.org/abs/2024.01001v1" rel="alternate" type="text/html"/>
    <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""

        responses.add(
            responses.GET,
            "http://export.arxiv.org/api/query",
            body=mock_xml,
            status=200,
            content_type="application/xml",
        )

        harvester = ArxivHarvester(["cs.LG"], days_back=7)
        papers = harvester._fetch_category_papers(
            "cs.LG", datetime.now() - timedelta(days=7)
        )

        assert len(papers) == 1
        paper = papers[0]
        assert paper.id == "2024.01001v1"
        assert paper.title == "Test Paper Title"
        assert paper.source == "arxiv"
        assert len(paper.authors) == 2
        assert "John Doe" in paper.authors

    def test_harvest_no_papers(self):
        """Test harvesting when no papers are found."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "http://export.arxiv.org/api/query",
                body="<?xml version='1.0' encoding='UTF-8'?><feed></feed>",
                status=200,
            )

            harvester = ArxivHarvester(["cs.AI"], days_back=7)
            papers = harvester.harvest()

            assert len(papers) == 0


class TestPapersWithCodeHarvester:
    """Test PapersWithCode harvesting."""

    @responses.activate
    def test_harvest_trending_papers(self):
        """Test fetching trending papers from PapersWithCode."""
        # Mock PapersWithCode API response
        mock_response = {
            "results": [
                {
                    "id": "pwc-1",
                    "title": "Trending ML Paper",
                    "authors": ["Alice Johnson", "Bob Wilson"],
                    "abstract": "This paper is trending on PapersWithCode",
                    "published": "2024-01-15T00:00:00Z",
                    "url_abs": "https://arxiv.org/abs/2024.01002",
                    "github_url": "https://github.com/alice/trending-ml",
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://paperswithcode.com/api/v1/papers/",
            json=mock_response,
            status=200,
        )

        harvester = PapersWithCodeHarvester(days_back=7)
        papers = harvester.harvest()

        assert len(papers) == 1
        paper = papers[0]
        assert paper.title == "Trending ML Paper"
        assert paper.source == "paperswithcode"
        assert paper.github_url == "https://github.com/alice/trending-ml"

    @responses.activate
    def test_harvest_api_error(self):
        """Test handling API errors gracefully."""
        responses.add(
            responses.GET, "https://paperswithcode.com/api/v1/papers/", status=500
        )

        harvester = PapersWithCodeHarvester(days_back=7)
        papers = harvester.harvest()

        assert len(papers) == 0


class TestHarvestPapers:
    """Test main harvest function."""

    def test_deduplication(self, mocker):
        """Test that duplicate papers are removed."""
        # Mock both harvesters to return papers with same title
        duplicate_paper1 = Paper(
            id="1",
            title="Same Title",
            authors=["Author 1"],
            abstract="Abstract 1",
            published_date=datetime.now(),
            url="url1",
            source="arxiv",
            categories=[],
        )

        duplicate_paper2 = Paper(
            id="2",
            title="Same Title",  # Same title
            authors=["Author 2"],
            abstract="Abstract 2",
            published_date=datetime.now(),
            url="url2",
            source="paperswithcode",
            categories=[],
        )

        unique_paper = Paper(
            id="3",
            title="Different Title",
            authors=["Author 3"],
            abstract="Abstract 3",
            published_date=datetime.now(),
            url="url3",
            source="arxiv",
            categories=[],
        )

        # Mock the harvesters
        mocker.patch.object(
            ArxivHarvester, "harvest", return_value=[duplicate_paper1, unique_paper]
        )
        mocker.patch.object(
            PapersWithCodeHarvester, "harvest", return_value=[duplicate_paper2]
        )

        papers = harvest_papers(["cs.AI"], days_back=7)

        # Should have 2 unique papers (duplicates removed)
        assert len(papers) == 2
        titles = [p.title for p in papers]
        assert "Same Title" in titles
        assert "Different Title" in titles
