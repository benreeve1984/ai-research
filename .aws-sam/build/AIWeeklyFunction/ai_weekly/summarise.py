"""LLM-based paper summarization."""

import logging
from typing import List
from .harvest import Paper


logger = logging.getLogger(__name__)


class LLMClient:
    """Base class for LLM clients."""

    def generate_summary(self, paper: Paper) -> str:
        """Generate summary for a paper."""
        raise NotImplementedError

    def generate_intro(self, papers: List[Paper]) -> str:
        """Generate intro summary for all papers."""
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI GPT client."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

        try:
            import openai

            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")

    def generate_summary(self, paper: Paper) -> str:
        """Generate summary for a single paper."""
        prompt = f"""Analyze this research paper and provide a structured summary:

Title: {paper.title}
Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}
Abstract: {paper.abstract}

Please provide:
1. Primary contribution (≤20 words)
2. Practitioner impact (≤30 words)
3. One-line method description

Format as structured text, not bullet points."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI research expert who writes concise, "
                            "technical summaries."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.3,
            )

            content = response.choices[0].message.content
            return content.strip() if content else "Summary generation failed."

        except Exception as e:
            logger.error(f"OpenAI API error for paper {paper.title[:50]}...: {e}")
            return "Summary generation failed."

    def generate_intro(self, papers: List[Paper]) -> str:
        """Generate executive summary intro."""
        paper_titles = "\n".join([f"- {paper.title}" for paper in papers])

        prompt = (
            f"Write a 120-word executive summary for this week's top AI research papers. "
            f"List 3 dominant themes across these papers:\n\n"
            f"Papers:\n{paper_titles}\n\n"
            f"Focus on overarching trends and themes that connect multiple papers, "
            f"rather than individual paper details."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI research analyst who identifies trends "
                            "and themes in academic research."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=180,
                temperature=0.4,
            )

            content = response.choices[0].message.content
            return content.strip() if content else "Summary generation failed."

        except Exception as e:
            logger.error(f"OpenAI API error for intro generation: {e}")
            return (
                "This week's AI research showcases continued progress across "
                "machine learning, computer vision, and natural language processing domains."
            )


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model

        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "Anthropic library not installed. Run: pip install anthropic"
            )

    def generate_summary(self, paper: Paper) -> str:
        """Generate summary for a single paper."""
        prompt = f"""Analyze this research paper and provide a structured summary:

Title: {paper.title}
Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}
Abstract: {paper.abstract}

Please provide:
1. Primary contribution (≤20 words)
2. Practitioner impact (≤30 words)
3. One-line method description

Format as structured text, not bullet points."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            text_content = getattr(response.content[0], "text", None)
            return (
                text_content.strip() if text_content else "Summary generation failed."
            )

        except Exception as e:
            logger.error(f"Anthropic API error for paper {paper.title[:50]}...: {e}")
            return "Summary generation failed."

    def generate_intro(self, papers: List[Paper]) -> str:
        """Generate executive summary intro."""
        paper_titles = "\n".join([f"- {paper.title}" for paper in papers])

        prompt = (
            f"Write a 120-word executive summary for this week's top AI research papers. "
            f"List 3 dominant themes across these papers:\n\n"
            f"Papers:\n{paper_titles}\n\n"
            f"Focus on overarching trends and themes that connect multiple papers, "
            f"rather than individual paper details."
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=180,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}],
            )

            text_content = getattr(response.content[0], "text", None)
            return (
                text_content.strip() if text_content else "Summary generation failed."
            )

        except Exception as e:
            logger.error(f"Anthropic API error for intro generation: {e}")
            return (
                "This week's AI research showcases continued progress across "
                "machine learning, computer vision, and natural language processing domains."
            )


def create_llm_client(backend: str, api_key: str, model: str) -> LLMClient:
    """Factory function to create LLM client."""
    if backend.lower() == "openai":
        return OpenAIClient(api_key, model)
    elif backend.lower() == "anthropic":
        return AnthropicClient(api_key, model)
    else:
        raise ValueError(f"Unsupported LLM backend: {backend}")


def summarize_papers(
    papers: List[Paper], backend: str, api_key: str, model: str
) -> tuple[List[Paper], str]:
    """Summarize papers and generate intro."""

    if not api_key:
        logger.error(f"No API key provided for {backend}")
        # Return papers with placeholder summaries
        for paper in papers:
            paper.summary = "Summary generation disabled - no API key provided."
        intro = "AI research summary generation is currently disabled."
        return papers, intro

    logger.info(f"Generating summaries using {backend} ({model})")

    try:
        client = create_llm_client(backend, api_key, model)

        # Generate individual paper summaries
        for i, paper in enumerate(papers):
            logger.debug(
                f"Generating summary for paper {i+1}/{len(papers)}: {paper.title[:50]}..."
            )
            summary = client.generate_summary(paper)
            paper.summary = summary

        # Generate intro summary
        logger.info("Generating executive summary intro")
        intro = client.generate_intro(papers)

        logger.info("Summarization completed")
        return papers, intro

    except Exception as e:
        logger.error(f"Error during summarization: {e}")
        # Return papers with error summaries
        for paper in papers:
            paper.summary = "Summary generation failed due to technical error."
        intro = (
            "This week's AI research summary could not be generated "
            "due to technical difficulties."
        )
        return papers, intro
