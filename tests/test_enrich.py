"""Tests for paper enrichment functionality."""

import responses
from unittest.mock import Mock, patch
from src.ai_weekly.enrich import SemanticScholarEnricher, GitHubEnricher, enrich_papers
from src.ai_weekly.harvest import Paper
from datetime import datetime


class TestSemanticScholarEnricher:
    """Test SemanticScholar enrichment."""

    def test_init_with_api_key(self):
        """Test enricher initialization with API key."""
        enricher = SemanticScholarEnricher("test-api-key")

        assert enricher.api_key == "test-api-key"
        assert "X-API-KEY" in enricher.session.headers
        assert enricher.session.headers["X-API-KEY"] == "test-api-key"

    def test_init_without_api_key(self):
        """Test enricher initialization without API key."""
        enricher = SemanticScholarEnricher()

        assert enricher.api_key is None
        assert "X-API-KEY" not in enricher.session.headers

    @responses.activate
    def test_enrich_paper_arxiv_success(self, sample_paper):
        """Test successful paper enrichment by arXiv ID."""
        mock_response = {
            "paperId": "test-paper-id",
            "title": "Test Paper",
            "citationCount": 42,
        }

        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/arXiv:2024.01001",
            json=mock_response,
            status=200,
        )

        # Mock embedding response
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/test-paper-id/embedding",
            json={"embedding": [0.1, 0.2, 0.3]},
            status=200,
        )

        enricher = SemanticScholarEnricher("test-key")
        enriched_paper = enricher.enrich_paper(sample_paper)

        assert enriched_paper.citation_count == 42
        assert enriched_paper.specter2_embedding == [0.1, 0.2, 0.3]

    @responses.activate
    def test_enrich_paper_title_search(self, sample_paper):
        """Test paper enrichment by title search."""
        # ArXiv search fails
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/arXiv:2024.01001",
            status=404,
        )

        # Title search succeeds
        mock_response = {
            "data": [
                {
                    "paperId": "title-paper-id",
                    "title": "A Novel Approach to Machine Learning",
                    "citationCount": 25,
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/search",
            json=mock_response,
            status=200,
        )

        enricher = SemanticScholarEnricher("test-key")
        enriched_paper = enricher.enrich_paper(sample_paper)

        assert enriched_paper.citation_count == 25

    @responses.activate
    def test_enrich_paper_not_found(self, sample_paper):
        """Test paper enrichment when paper not found."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/arXiv:2024.01001",
            status=404,
        )

        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/search",
            json={"data": []},
            status=200,
        )

        enricher = SemanticScholarEnricher("test-key")
        enriched_paper = enricher.enrich_paper(sample_paper)

        assert enriched_paper.citation_count == 0

    def test_titles_similar(self):
        """Test title similarity checking."""
        enricher = SemanticScholarEnricher()

        # Exact match
        assert enricher._titles_similar("Test Title", "Test Title")

        # Similar titles
        assert enricher._titles_similar(
            "A Novel Approach to Machine Learning", "Novel Approach to Machine Learning"
        )

        # Different titles
        assert not enricher._titles_similar(
            "Machine Learning Paper", "Computer Vision Study"
        )

    @responses.activate
    def test_enrich_paper_api_error(self, sample_paper):
        """Test paper enrichment with API error."""
        responses.add(
            responses.GET,
            "https://api.semanticscholar.org/graph/v1/paper/arXiv:2024.01001",
            status=500,
        )

        enricher = SemanticScholarEnricher("test-key")
        enriched_paper = enricher.enrich_paper(sample_paper)

        assert enriched_paper.citation_count == 0


class TestGitHubEnricher:
    """Test GitHub enrichment."""

    def test_init_with_token(self):
        """Test enricher initialization with token."""
        enricher = GitHubEnricher("test-token")

        assert enricher.token == "test-token"
        assert "Authorization" in enricher.session.headers
        assert enricher.session.headers["Authorization"] == "token test-token"

    def test_init_without_token(self):
        """Test enricher initialization without token."""
        enricher = GitHubEnricher()

        assert enricher.token is None
        assert "Authorization" not in enricher.session.headers

    @responses.activate
    def test_enrich_paper_with_github_url(self, sample_paper):
        """Test enriching paper that already has GitHub URL."""
        mock_response = {"stargazers_count": 150, "name": "ml-project"}

        responses.add(
            responses.GET,
            "https://api.github.com/repos/johndoe/ml-project",
            json=mock_response,
            status=200,
        )

        enricher = GitHubEnricher("test-token")
        enriched_paper = enricher.enrich_paper(sample_paper)

        assert enriched_paper.github_stars == 150

    def test_enrich_paper_extract_github_url(self):
        """Test extracting GitHub URL from paper text."""
        paper = Paper(
            id="test",
            title="Test Paper",
            authors=["Author"],
            abstract="Code available at https://github.com/user/repo",
            published_date=datetime.now(),
            url="test-url",
            source="arxiv",
            categories=[],
        )

        enricher = GitHubEnricher("test-token")

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.github.com/repos/user/repo",
                json={"stargazers_count": 75},
                status=200,
            )

            enriched_paper = enricher.enrich_paper(paper)

            assert enriched_paper.github_url == "https://github.com/user/repo"
            assert enriched_paper.github_stars == 75

    def test_extract_github_url_patterns(self):
        """Test GitHub URL extraction patterns."""
        enricher = GitHubEnricher()

        # Full URL
        url = enricher._extract_github_url("Code at https://github.com/user/repo")
        assert url == "https://github.com/user/repo"

        # URL without protocol
        url = enricher._extract_github_url("See github.com/user/repo")
        assert url == "https://github.com/user/repo"

        # No GitHub URL
        url = enricher._extract_github_url("No code repository mentioned")
        assert url is None

    @responses.activate
    def test_get_repo_stars_not_found(self):
        """Test getting stars for non-existent repository."""
        responses.add(
            responses.GET, "https://api.github.com/repos/user/nonexistent", status=404
        )

        enricher = GitHubEnricher("test-token")
        stars = enricher._get_repo_stars("https://github.com/user/nonexistent")

        assert stars == 0

    def test_get_repo_stars_invalid_url(self):
        """Test getting stars for invalid GitHub URL."""
        enricher = GitHubEnricher("test-token")
        stars = enricher._get_repo_stars("https://invalid-url.com")

        assert stars == 0


class TestEnrichPapers:
    """Test main enrich function."""

    @patch("src.ai_weekly.enrich.SemanticScholarEnricher")
    @patch("src.ai_weekly.enrich.GitHubEnricher")
    def test_enrich_papers_success(
        self, mock_gh_enricher, mock_s2_enricher, sample_papers
    ):
        """Test successful paper enrichment."""
        # Mock enrichers
        mock_s2_instance = Mock()
        mock_gh_instance = Mock()
        mock_s2_enricher.return_value = mock_s2_instance
        mock_gh_enricher.return_value = mock_gh_instance

        # Mock enrichment methods to return the same paper
        mock_s2_instance.enrich_paper.side_effect = lambda p: p
        mock_gh_instance.enrich_paper.side_effect = lambda p: p

        enriched_papers = enrich_papers(
            sample_papers,
            semantic_scholar_api_key="test-s2-key",
            github_token="test-github-token",
        )

        assert len(enriched_papers) == len(sample_papers)

        # Verify enrichers were called
        assert mock_s2_instance.enrich_paper.call_count == len(sample_papers)
        assert mock_gh_instance.enrich_paper.call_count == len(sample_papers)

    @patch("src.ai_weekly.enrich.SemanticScholarEnricher")
    @patch("src.ai_weekly.enrich.GitHubEnricher")
    def test_enrich_papers_no_keys(
        self, mock_gh_enricher, mock_s2_enricher, sample_papers
    ):
        """Test paper enrichment without API keys."""
        # Mock enrichers
        mock_s2_instance = Mock()
        mock_gh_instance = Mock()
        mock_s2_enricher.return_value = mock_s2_instance
        mock_gh_enricher.return_value = mock_gh_instance

        mock_s2_instance.enrich_paper.side_effect = lambda p: p
        mock_gh_instance.enrich_paper.side_effect = lambda p: p

        enriched_papers = enrich_papers(sample_papers)

        # Should still work without keys
        assert len(enriched_papers) == len(sample_papers)

        # Enrichers should be created with None
        mock_s2_enricher.assert_called_once_with(None)
        mock_gh_enricher.assert_called_once_with(None)
