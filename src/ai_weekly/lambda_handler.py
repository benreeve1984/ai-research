"""AWS Lambda handler for the AI Weekly pipeline."""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any

from .config import load_config
from .harvest import harvest_papers
from .enrich import enrich_papers
from .rank import rank_papers
from .summarise import summarize_papers
from .publish import publish_report


# Configure structured logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for the AI Weekly pipeline.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response dictionary with execution results
    """

    start_time = datetime.now()

    logger.info(
        "Starting AI Weekly pipeline execution",
        extra={
            "event": event,
            "request_id": getattr(context, "aws_request_id", "unknown"),
        },
    )

    try:
        # Load configuration
        logger.info("Loading configuration")
        config = load_config()

        # Log configuration (without sensitive data)
        logger.info(
            "Configuration loaded",
            extra={
                "report_bucket": config.report_bucket,
                "llm_backend": config.llm_backend,
                "llm_model": config.llm_model,
                "arxiv_categories": config.arxiv_categories,
                "days_lookback": config.days_lookback,
                "top_k_papers": config.top_k_papers,
                "has_openai_key": bool(config.openai_api_key),
                "has_anthropic_key": bool(config.anthropic_api_key),
                "has_github_token": bool(config.github_token),
                "subscribers_count": (
                    len(config.subscribers) if config.subscribers else 0
                ),
            },
        )

        # Step 1: Harvest papers
        logger.info("Step 1: Harvesting papers")
        papers = harvest_papers(
            categories=config.arxiv_categories, days_back=config.days_lookback
        )

        if not papers:
            logger.warning("No papers found to process")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "status": "completed",
                        "message": "No papers found to process",
                        "papers_count": 0,
                        "execution_time_seconds": (
                            datetime.now() - start_time
                        ).total_seconds(),
                    }
                ),
            }

        logger.info(f"Harvested {len(papers)} papers")

        # Step 2: Enrich papers
        logger.info("Step 2: Enriching papers with external data")
        papers = enrich_papers(
            papers=papers,
            semantic_scholar_api_key=config.semantic_scholar_api_key,
            github_token=config.github_token,
        )

        # Step 3: Rank papers
        logger.info("Step 3: Ranking papers")
        top_papers = rank_papers(
            papers=papers,
            top_k=config.top_k_papers,
            citation_weight=config.citation_weight,
            github_weight=config.github_weight,
            social_weight=config.social_weight,
        )

        # Step 4: Generate summaries
        logger.info("Step 4: Generating summaries")

        # Select API key based on backend
        if config.llm_backend.lower() == "openai":
            api_key = config.openai_api_key
        elif config.llm_backend.lower() == "anthropic":
            api_key = config.anthropic_api_key
        else:
            raise ValueError(f"Unsupported LLM backend: {config.llm_backend}")

        summarized_papers, intro = summarize_papers(
            papers=top_papers,
            backend=config.llm_backend,
            api_key=api_key,
            model=config.llm_model,
        )

        # Step 5: Publish report
        logger.info("Step 5: Publishing report")
        publish_result = publish_report(
            papers=summarized_papers,
            intro=intro,
            bucket_name=config.report_bucket,
            sender_email=config.ses_sender,
            recipients=config.subscribers,
        )

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Prepare response
        response = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "completed",
                    "message": "AI Weekly pipeline executed successfully",
                    "papers_harvested": len(papers),
                    "papers_published": len(summarized_papers),
                    "execution_time_seconds": execution_time,
                    "publish_result": publish_result,
                }
            ),
        }

        logger.info(
            "Pipeline execution completed successfully",
            extra={
                "papers_harvested": len(papers),
                "papers_published": len(summarized_papers),
                "execution_time_seconds": execution_time,
                "latest_url": publish_result.get("latest_url"),
                "email_sent": publish_result.get("email_sent", False),
            },
        )

        return response

    except Exception as e:
        # Calculate execution time for error case
        execution_time = (datetime.now() - start_time).total_seconds()

        logger.error(
            "Pipeline execution failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time_seconds": execution_time,
            },
            exc_info=True,
        )

        # Return error response
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "message": f"Pipeline execution failed: {str(e)}",
                    "error_type": type(e).__name__,
                    "execution_time_seconds": execution_time,
                }
            ),
        }


def run_pipeline():
    """
    Entry point for local testing and development.
    Can be called directly without Lambda context.
    """

    class MockContext:
        aws_request_id = "local-test"

    # Mock Lambda event
    event = {"source": "local-test", "time": datetime.now().isoformat()}

    # Run pipeline
    result = lambda_handler(event, MockContext())

    # Print result
    print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    # Allow running directly for testing
    run_pipeline()
