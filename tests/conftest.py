"""Pytest configuration and fixtures."""

import pytest
from datetime import datetime
from typing import List
from src.ai_weekly.harvest import Paper


@pytest.fixture
def sample_paper():
    """Sample paper for testing."""
    return Paper(
        id="2024.01001",
        title="A Novel Approach to Machine Learning",
        authors=["John Doe", "Jane Smith"],
        abstract="This paper presents a novel approach to machine learning that improves accuracy by 10%.",
        published_date=datetime(2024, 1, 15),
        url="https://arxiv.org/abs/2024.01001",
        source="arxiv",
        categories=["cs.LG", "cs.AI"],
        citation_count=42,
        github_url="https://github.com/johndoe/ml-project",
        github_stars=150,
        score=3.5,
    )


@pytest.fixture
def sample_papers(sample_paper):
    """List of sample papers for testing."""
    papers = []

    # Create variations of the sample paper
    for i in range(5):
        paper = Paper(
            id=f"2024.0100{i+1}",
            title=f"Paper Title {i+1}",
            authors=[f"Author {i+1}A", f"Author {i+1}B"],
            abstract=f"Abstract for paper {i+1}",
            published_date=datetime(2024, 1, 15 + i),
            url=f"https://arxiv.org/abs/2024.0100{i+1}",
            source="arxiv",
            categories=["cs.LG"],
            citation_count=10 * (i + 1),
            github_url=(
                f"https://github.com/author{i+1}/project{i+1}" if i % 2 == 0 else None
            ),
            github_stars=50 * (i + 1) if i % 2 == 0 else None,
            score=float(i + 1),
        )
        papers.append(paper)

    return papers


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    from src.ai_weekly.config import Config

    return Config(
        report_bucket="test-bucket",
        openai_api_key="test-openai-key",
        anthropic_api_key="test-anthropic-key",
        semantic_scholar_api_key="test-s2-key",
        github_token="test-github-token",
        llm_backend="openai",
        llm_model="gpt-4o-mini",
        subscribers=["test@example.com"],
        ses_sender="sender@example.com",
    )
