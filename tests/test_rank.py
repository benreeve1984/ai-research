"""Tests for paper ranking functionality."""

import pytest
import math
from src.ai_weekly.rank import (
    normalize_github_stars,
    calculate_paper_score,
    rank_papers,
)


class TestNormalizeGithubStars:
    """Test GitHub stars normalization."""

    def test_normalize_stars(self, sample_papers):
        """Test basic star normalization."""
        papers = normalize_github_stars(sample_papers)

        # Check that _normalized_stars attribute is added
        for paper in papers:
            assert hasattr(paper, "_normalized_stars")
            assert 0 <= paper._normalized_stars <= 1

    def test_normalize_all_zero_stars(self, sample_papers):
        """Test normalization when all papers have zero stars."""
        # Set all stars to 0
        for paper in sample_papers:
            paper.github_stars = 0

        papers = normalize_github_stars(sample_papers)

        # All should be normalized to 0
        for paper in papers:
            assert paper._normalized_stars == 0.0

    def test_normalize_same_stars(self, sample_papers):
        """Test normalization when all papers have same star count."""
        # Set all stars to same value
        for paper in sample_papers:
            paper.github_stars = 100

        papers = normalize_github_stars(sample_papers)

        # All should be normalized to 0 (no variance)
        for paper in papers:
            assert paper._normalized_stars == 0.0

    def test_normalize_empty_list(self):
        """Test normalization with empty paper list."""
        papers = normalize_github_stars([])
        assert papers == []


class TestCalculatePaperScore:
    """Test paper scoring calculation."""

    def test_calculate_score_with_citations(self, sample_paper):
        """Test score calculation with citations."""
        sample_paper.citation_count = 100
        sample_paper.github_stars = 200
        sample_paper._normalized_stars = 0.8

        score = calculate_paper_score(sample_paper)

        # Expected: 0.5 * log(101) + 0.3 * 0.8 + 0.2 * 0
        expected = 0.5 * math.log(101) + 0.3 * 0.8 + 0.2 * 0
        assert abs(score - expected) < 0.001

    def test_calculate_score_no_citations(self, sample_paper):
        """Test score calculation with no citations."""
        sample_paper.citation_count = 0
        sample_paper.github_stars = 50
        sample_paper._normalized_stars = 0.3

        score = calculate_paper_score(sample_paper)

        # Expected: 0.5 * log(1) + 0.3 * 0.3 + 0.2 * 0 = 0.09
        expected = 0.5 * 0 + 0.3 * 0.3 + 0.2 * 0
        assert abs(score - expected) < 0.001

    def test_calculate_score_none_values(self, sample_paper):
        """Test score calculation with None values."""
        sample_paper.citation_count = None
        sample_paper.github_stars = None
        sample_paper._normalized_stars = 0.0

        score = calculate_paper_score(sample_paper)

        # Should handle None values gracefully
        expected = 0.5 * math.log(1) + 0.3 * 0.0 + 0.2 * 0
        assert abs(score - expected) < 0.001

    def test_custom_weights(self, sample_paper):
        """Test score calculation with custom weights."""
        sample_paper.citation_count = 50
        sample_paper._normalized_stars = 0.5

        score = calculate_paper_score(
            sample_paper, citation_weight=0.7, github_weight=0.2, social_weight=0.1
        )

        expected = 0.7 * math.log(51) + 0.2 * 0.5 + 0.1 * 0
        assert abs(score - expected) < 0.001


class TestRankPapers:
    """Test paper ranking functionality."""

    def test_rank_papers_basic(self, sample_papers):
        """Test basic paper ranking."""
        ranked = rank_papers(sample_papers, top_k=3)

        # Should return top 3 papers
        assert len(ranked) == 3

        # Should be sorted by score (descending)
        scores = [p.score for p in ranked]
        assert scores == sorted(scores, reverse=True)

        # All papers should have scores
        for paper in ranked:
            assert paper.score is not None

    def test_rank_papers_more_than_available(self, sample_papers):
        """Test ranking when requesting more papers than available."""
        ranked = rank_papers(sample_papers, top_k=10)

        # Should return all available papers
        assert len(ranked) == len(sample_papers)

    def test_rank_empty_list(self):
        """Test ranking empty paper list."""
        ranked = rank_papers([])
        assert ranked == []

    def test_rank_single_paper(self, sample_paper):
        """Test ranking single paper."""
        ranked = rank_papers([sample_paper], top_k=5)

        assert len(ranked) == 1
        assert ranked[0] == sample_paper
        assert ranked[0].score is not None

    def test_ranking_order(self):
        """Test that papers are ranked in correct order."""
        from src.ai_weekly.harvest import Paper
        from datetime import datetime

        # Create papers with known citation counts
        high_citation_paper = Paper(
            id="high",
            title="High Citations",
            authors=[],
            abstract="",
            published_date=datetime.now(),
            url="",
            source="arxiv",
            categories=[],
            citation_count=1000,
            github_stars=0,
        )

        low_citation_paper = Paper(
            id="low",
            title="Low Citations",
            authors=[],
            abstract="",
            published_date=datetime.now(),
            url="",
            source="arxiv",
            categories=[],
            citation_count=10,
            github_stars=0,
        )

        papers = [low_citation_paper, high_citation_paper]
        ranked = rank_papers(papers, top_k=2)

        # High citation paper should be ranked first
        assert ranked[0].id == "high"
        assert ranked[1].id == "low"
        assert ranked[0].score > ranked[1].score
