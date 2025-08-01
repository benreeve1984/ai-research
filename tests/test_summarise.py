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

    @patch('builtins.__import__')
    def test_init_success(self, mock_import):
        """Test successful OpenAI client initialization."""
        mock_openai = Mock()
        mock_openai.OpenAI.return_value = Mock()
        
        def side_effect(name, *args, **kwargs):
            if name == 'openai':
                return mock_openai
            # For other imports, call the real import
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect

        client = OpenAIClient("test-key", "gpt-4o-mini")

        assert client.api_key == "test-key"
        assert client.model == "gpt-4o-mini"
        mock_openai.OpenAI.assert_called_once_with(api_key="test-key")

    @patch('builtins.__import__')
    def test_init_import_error(self, mock_import):
        """Test OpenAI client initialization with import error."""
        def side_effect(name, *args, **kwargs):
            if name == 'openai':
                raise ImportError("No module named 'openai'")
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
        with pytest.raises(ImportError, match="OpenAI library not installed"):
            OpenAIClient("test-key")

    @patch('builtins.__import__')
    def test_generate_summary(self, mock_import, sample_paper):
        """Test paper summary generation."""
        mock_openai = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test summary content"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client
        
        def side_effect(name, *args, **kwargs):
            if name == 'openai':
                return mock_openai
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect

        client = OpenAIClient("test-key")
        summary = client.generate_summary(sample_paper)

        assert summary == "Test summary content"
        mock_client.chat.completions.create.assert_called_once()

    @patch('builtins.__import__')
    def test_generate_summary_api_error(self, mock_import, sample_paper):
        """Test summary generation with API error."""
        mock_openai = Mock()
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.OpenAI.return_value = mock_client
        
        def side_effect(name, *args, **kwargs):
            if name == 'openai':
                return mock_openai
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect

        client = OpenAIClient("test-key")
        summary = client.generate_summary(sample_paper)

        assert summary == "Summary generation failed."

    @patch('builtins.__import__')
    def test_generate_intro(self, mock_import, sample_papers):
        """Test intro generation."""
        mock_openai = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Executive summary content"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client
        
        def side_effect(name, *args, **kwargs):
            if name == 'openai':
                return mock_openai
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect

        client = OpenAIClient("test-key")
        intro = client.generate_intro(sample_papers)

        assert intro == "Executive summary content"


class TestAnthropicClient:
    """Test Anthropic client functionality."""

    @patch('builtins.__import__')
    def test_init_success(self, mock_import):
        """Test successful Anthropic client initialization."""
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = Mock()
        
        def side_effect(name, *args, **kwargs):
            if name == 'anthropic':
                return mock_anthropic
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect

        client = AnthropicClient("test-key", "claude-3-opus-20240229")

        assert client.api_key == "test-key"
        assert client.model == "claude-3-opus-20240229"
        mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")

    @patch('builtins.__import__')
    def test_init_import_error(self, mock_import):
        """Test Anthropic client initialization with import error."""
        def side_effect(name, *args, **kwargs):
            if name == 'anthropic':
                raise ImportError("No module named 'anthropic'")
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
        with pytest.raises(ImportError, match="Anthropic library not installed"):
            AnthropicClient("test-key")

    @patch('builtins.__import__')
    def test_generate_summary(self, mock_import, sample_paper):
        """Test paper summary generation."""
        mock_anthropic = Mock()
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Anthropic summary content"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client
        
        def side_effect(name, *args, **kwargs):
            if name == 'anthropic':
                return mock_anthropic
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect

        client = AnthropicClient("test-key")
        summary = client.generate_summary(sample_paper)

        assert summary == "Anthropic summary content"
        mock_client.messages.create.assert_called_once()


class TestCreateLLMClient:
    """Test LLM client factory function."""

    @patch('builtins.__import__')
    def test_create_openai_client(self, mock_import):
        """Test creating OpenAI client."""
        mock_openai = Mock()
        mock_openai.OpenAI.return_value = Mock()
        
        def side_effect(name, *args, **kwargs):
            if name == 'openai':
                return mock_openai
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
        client = create_llm_client("openai", "test-key", "gpt-4o-mini")
        assert isinstance(client, OpenAIClient)

    @patch('builtins.__import__')
    def test_create_anthropic_client(self, mock_import):
        """Test creating Anthropic client."""
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = Mock()
        
        def side_effect(name, *args, **kwargs):
            if name == 'anthropic':
                return mock_anthropic
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
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
