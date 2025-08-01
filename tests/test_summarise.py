"""Tests for LLM summarization functionality."""

import pytest
from unittest.mock import Mock, patch
from src.ai_weekly.summarise import (
    OpenAIClient,
    AnthropicClient,
    create_llm_client,
    summarize_papers,
)


class TestOpenAIClient:
    """Test OpenAI client functionality."""

    def test_init_success(self):
        """Test successful OpenAI client initialization."""
        with patch("src.ai_weekly.summarise.openai") as mock_openai:
            mock_openai.OpenAI.return_value = Mock()

            client = OpenAIClient("test-key", "gpt-4o-mini")

            assert client.api_key == "test-key"
            assert client.model == "gpt-4o-mini"
            mock_openai.OpenAI.assert_called_once_with(api_key="test-key")

    def test_init_import_error(self):
        """Test OpenAI client initialization with import error."""
        with patch("src.ai_weekly.summarise.openai", side_effect=ImportError()):
            with pytest.raises(ImportError, match="OpenAI library not installed"):
                OpenAIClient("test-key")

    def test_generate_summary(self, sample_paper):
        """Test paper summary generation."""
        with patch("src.ai_weekly.summarise.openai") as mock_openai:
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Test summary content"

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client

            client = OpenAIClient("test-key")
            summary = client.generate_summary(sample_paper)

            assert summary == "Test summary content"
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_summary_api_error(self, sample_paper):
        """Test summary generation with API error."""
        with patch("src.ai_weekly.summarise.openai") as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.OpenAI.return_value = mock_client

            client = OpenAIClient("test-key")
            summary = client.generate_summary(sample_paper)

            assert summary == "Summary generation failed."

    def test_generate_intro(self, sample_papers):
        """Test intro generation."""
        with patch("src.ai_weekly.summarise.openai") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Executive summary content"

            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client

            client = OpenAIClient("test-key")
            intro = client.generate_intro(sample_papers)

            assert intro == "Executive summary content"


class TestAnthropicClient:
    """Test Anthropic client functionality."""

    def test_init_success(self):
        """Test successful Anthropic client initialization."""
        with patch("src.ai_weekly.summarise.anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value = Mock()

            client = AnthropicClient("test-key", "claude-3-opus-20240229")

            assert client.api_key == "test-key"
            assert client.model == "claude-3-opus-20240229"
            mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")

    def test_init_import_error(self):
        """Test Anthropic client initialization with import error."""
        with patch("src.ai_weekly.summarise.anthropic", side_effect=ImportError()):
            with pytest.raises(ImportError, match="Anthropic library not installed"):
                AnthropicClient("test-key")

    def test_generate_summary(self, sample_paper):
        """Test paper summary generation."""
        with patch("src.ai_weekly.summarise.anthropic") as mock_anthropic:
            # Mock Anthropic response
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "Anthropic summary content"

            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client

            client = AnthropicClient("test-key")
            summary = client.generate_summary(sample_paper)

            assert summary == "Anthropic summary content"
            mock_client.messages.create.assert_called_once()


class TestCreateLLMClient:
    """Test LLM client factory function."""

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        with patch("src.ai_weekly.summarise.openai"):
            client = create_llm_client("openai", "test-key", "gpt-4o-mini")
            assert isinstance(client, OpenAIClient)

    def test_create_anthropic_client(self):
        """Test creating Anthropic client."""
        with patch("src.ai_weekly.summarise.anthropic"):
            client = create_llm_client(
                "anthropic", "test-key", "claude-3-opus-20240229"
            )
            assert isinstance(client, AnthropicClient)

    def test_unsupported_backend(self):
        """Test creating client with unsupported backend."""
        with pytest.raises(ValueError, match="Unsupported LLM backend: invalid"):
            create_llm_client("invalid", "test-key", "model")


class TestSummarizePapers:
    """Test main summarization function."""

    def test_summarize_papers_success(self, sample_papers):
        """Test successful paper summarization."""
        with patch("src.ai_weekly.summarise.create_llm_client") as mock_factory:
            mock_client = Mock()
            mock_client.generate_summary.return_value = "Mock summary"
            mock_client.generate_intro.return_value = "Mock intro"
            mock_factory.return_value = mock_client

            papers, intro = summarize_papers(
                sample_papers, backend="openai", api_key="test-key", model="gpt-4o-mini"
            )

            assert len(papers) == len(sample_papers)
            assert intro == "Mock intro"

            # Check that all papers have summaries
            for paper in papers:
                assert paper.summary == "Mock summary"

    def test_summarize_papers_no_api_key(self, sample_papers):
        """Test summarization without API key."""
        papers, intro = summarize_papers(
            sample_papers, backend="openai", api_key=None, model="gpt-4o-mini"
        )

        assert len(papers) == len(sample_papers)
        assert "disabled" in intro.lower()

        # Check that all papers have placeholder summaries
        for paper in papers:
            assert "disabled" in paper.summary.lower()

    def test_summarize_papers_api_error(self, sample_papers):
        """Test summarization with API error."""
        with patch("src.ai_weekly.summarise.create_llm_client") as mock_factory:
            mock_factory.side_effect = Exception("API Error")

            papers, intro = summarize_papers(
                sample_papers, backend="openai", api_key="test-key", model="gpt-4o-mini"
            )

            assert len(papers) == len(sample_papers)
            assert "technical difficulties" in intro.lower()

            # Check that all papers have error summaries
            for paper in papers:
                assert "failed" in paper.summary.lower()
