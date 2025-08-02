"""Configuration management for AI Weekly pipeline."""

import os
from typing import Optional, List
import json
import boto3
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    # S3 Configuration
    report_bucket: str
    history_path: str = "history/"
    latest_path: str = "latest/"

    # API Keys (from Secrets Manager)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    semantic_scholar_api_key: Optional[str] = None
    github_token: Optional[str] = None

    # LLM Configuration
    llm_backend: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4o-mini"

    # Email Configuration
    subscribers: Optional[List[str]] = None
    ses_sender: Optional[str] = None

    # Ranking weights
    citation_weight: float = 0.5
    github_weight: float = 0.3
    social_weight: float = 0.2

    # Paper collection
    arxiv_categories: Optional[List[str]] = None
    days_lookback: int = 7
    top_k_papers: int = 10

    def __post_init__(self):
        if self.arxiv_categories is None:
            self.arxiv_categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]


def load_config() -> Config:
    """Load configuration from environment variables and AWS Secrets Manager."""
    # Load from environment
    report_bucket = os.environ.get("REPORT_BUCKET", "")
    if not report_bucket:
        raise ValueError("REPORT_BUCKET environment variable must be set")

    config = Config(
        report_bucket=report_bucket,
        llm_backend=os.environ.get("LLM_BACKEND", "openai"),
        llm_model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        ses_sender=os.environ.get("SES_SENDER"),
        days_lookback=int(os.environ.get("DAYS_LOOKBACK", "7")),
        top_k_papers=int(os.environ.get("TOP_K_PAPERS", "10")),
    )

    # Parse subscribers if set
    subscribers_raw = os.environ.get("SUBSCRIBERS")
    if subscribers_raw:
        config.subscribers = [s.strip() for s in subscribers_raw.split(",")]

    # Load secrets from AWS Secrets Manager if available
    secret_name = os.environ.get("SECRET_NAME")
    if secret_name:
        try:
            session = boto3.session.Session()
            client = session.client(service_name="secretsmanager")

            response = client.get_secret_value(SecretId=secret_name)
            secrets = json.loads(response["SecretString"])

            config.openai_api_key = secrets.get("OPENAI_API_KEY")
            config.anthropic_api_key = secrets.get("ANTHROPIC_API_KEY")
            config.semantic_scholar_api_key = secrets.get("SEMANTIC_SCHOLAR_API_KEY")
            config.github_token = secrets.get("GITHUB_TOKEN")

        except Exception as e:
            print(f"Warning: Could not load secrets from Secrets Manager: {e}")
    else:
        # Fallback to environment variables for local development
        config.openai_api_key = os.environ.get("OPENAI_API_KEY")
        config.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        config.semantic_scholar_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        config.github_token = os.environ.get("GITHUB_TOKEN")

    return config
