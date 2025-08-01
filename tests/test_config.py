"""Tests for configuration functionality."""

import pytest
from unittest.mock import patch, Mock
from src.ai_weekly.config import Config, load_config


class TestConfig:
    """Test Config dataclass."""

    def test_config_defaults(self):
        """Test config with default values."""
        config = Config(report_bucket="test-bucket", openai_api_key="test-key")

        assert config.report_bucket == "test-bucket"
        assert config.openai_api_key == "test-key"
        assert config.llm_backend == "openai"
        assert config.llm_model == "gpt-4o-mini"
        assert config.arxiv_categories == ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]
        assert config.days_lookback == 7
        assert config.top_k_papers == 10
        assert config.citation_weight == 0.5
        assert config.github_weight == 0.3
        assert config.social_weight == 0.2

    def test_config_custom_values(self):
        """Test config with custom values."""
        config = Config(
            report_bucket="custom-bucket",
            openai_api_key="custom-key",
            llm_backend="anthropic",
            llm_model="claude-3-opus",
            arxiv_categories=["cs.AI"],
            days_lookback=14,
            top_k_papers=5,
            citation_weight=0.6,
            github_weight=0.3,
            social_weight=0.1,
        )

        assert config.report_bucket == "custom-bucket"
        assert config.llm_backend == "anthropic"
        assert config.llm_model == "claude-3-opus"
        assert config.arxiv_categories == ["cs.AI"]
        assert config.days_lookback == 14
        assert config.top_k_papers == 5
        assert config.citation_weight == 0.6


class TestLoadConfig:
    """Test config loading functionality."""

    @patch.dict(
        "os.environ",
        {
            "REPORT_BUCKET": "env-bucket",
            "LLM_BACKEND": "openai",
            "LLM_MODEL": "gpt-4o",
            "DAYS_LOOKBACK": "14",
            "TOP_K_PAPERS": "15",
        },
    )
    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        config = load_config()

        assert config.report_bucket == "env-bucket"
        assert config.llm_backend == "openai"
        assert config.llm_model == "gpt-4o"
        assert config.days_lookback == 14
        assert config.top_k_papers == 15

    @patch("boto3.session.Session")
    @patch.dict(
        "os.environ",
        {"REPORT_BUCKET": "test-bucket", "SECRET_NAME": "ai-weekly-secrets"},
    )
    def test_load_config_with_secrets_manager(self, mock_session):
        """Test loading config with AWS Secrets Manager."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_secrets_client = Mock()
        mock_session_instance.client.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.return_value = {
            "SecretString": (
                '{"OPENAI_API_KEY": "secret-openai-key", '
                '"GITHUB_TOKEN": "secret-github-token"}'
            )
        }

        config = load_config()

        assert config.report_bucket == "test-bucket"
        assert config.openai_api_key == "secret-openai-key"
        assert config.github_token == "secret-github-token"
        mock_secrets_client.get_secret_value.assert_called_once_with(
            SecretId="ai-weekly-secrets"
        )

    @patch("boto3.session.Session")
    @patch.dict(
        "os.environ",
        {"REPORT_BUCKET": "test-bucket", "SECRET_NAME": "ai-weekly-secrets"},
    )
    def test_load_config_secrets_manager_error(self, mock_session):
        """Test config loading when Secrets Manager fails."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        mock_secrets_client = Mock()
        mock_session_instance.client.return_value = mock_secrets_client
        mock_secrets_client.get_secret_value.side_effect = Exception("Access denied")

        # Should not raise exception, just skip secrets
        config = load_config()
        assert config.report_bucket == "test-bucket"
        assert config.openai_api_key is None

    @patch.dict(
        "os.environ",
        {
            "SUBSCRIBERS": "user1@example.com,user2@example.com",
            "REPORT_BUCKET": "test-bucket",
        },
    )
    def test_load_config_subscribers_list(self):
        """Test loading subscriber list from environment."""
        config = load_config()

        assert config.subscribers == ["user1@example.com", "user2@example.com"]

    @patch.dict(
        "os.environ",
        {
            "REPORT_BUCKET": "test-bucket",
            "LLM_BACKEND": "anthropic",
            "LLM_MODEL": "claude-3-opus",
        },
    )
    def test_load_config_llm_settings(self):
        """Test loading LLM settings from environment."""
        config = load_config()

        assert config.llm_backend == "anthropic"
        assert config.llm_model == "claude-3-opus"

    def test_load_config_missing_bucket(self):
        """Test config loading without required REPORT_BUCKET."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(
                ValueError, match="REPORT_BUCKET environment variable must be set"
            ):
                load_config()
