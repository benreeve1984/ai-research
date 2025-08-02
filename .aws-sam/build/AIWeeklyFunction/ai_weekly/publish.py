"""Publishing functionality for S3 and SES."""

import logging
from datetime import datetime
from typing import List, Optional, Union
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from .harvest import Paper


logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Generates markdown reports from papers."""

    @staticmethod
    def generate_report(papers: List[Paper], intro: str, date: datetime) -> str:
        """Generate markdown report."""
        date_str = date.strftime("%Y-%m-%d")

        # Front matter
        markdown = f"""---
title: "AI Research Weekly - {date_str}"
date: "{date.isoformat()}"
description: "Weekly digest of top AI research papers"
---

# AI Research Weekly - {date_str}

{intro}

## Featured Papers

"""

        # Add each paper
        for i, paper in enumerate(papers, 1):
            # Format authors (limit to 3 for brevity)
            authors_str = ", ".join(paper.authors[:3])
            if len(paper.authors) > 3:
                authors_str += " et al."

            # Format paper section
            markdown += f"### {i}. {paper.title}\n\n"
            markdown += f"**Authors:** {authors_str}  \n"
            markdown += (
                f"**Published:** {paper.published_date.strftime('%Y-%m-%d')}  \n"
            )

            if paper.citation_count is not None:
                markdown += f"**Citations:** {paper.citation_count}  \n"

            if paper.github_url and paper.github_stars is not None:
                markdown += (
                    f"**GitHub:** [{paper.github_url}]({paper.github_url}) "
                    f"({paper.github_stars} ⭐)  \n"
                )

            markdown += f"**Score:** {paper.score:.2f}  \n"
            markdown += f"**Link:** [{paper.url}]({paper.url})  \n\n"

            if paper.summary:
                markdown += f"{paper.summary}\n\n"

            markdown += "---\n\n"

        # Footer
        markdown += f"""
## Methodology

This digest was automatically generated using the following methodology:

1. **Paper Collection:** Harvested from arXiv (cs.AI, cs.LG, cs.CL, cs.CV) and PapersWithCode
   trending papers from the last 7 days
2. **Enrichment:** Enhanced with citation counts from Semantic Scholar and GitHub star counts
   where available
3. **Ranking:** Scored using formula: `0.5×log(citations+1) + 0.3×normalized_github_stars +
   0.2×social_buzz`
4. **Summarization:** Generated using LLM analysis of abstracts and titles

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

        return markdown


class S3Publisher:
    """Publishes reports to S3."""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3")

    def publish_report(self, markdown_content: str, date: datetime) -> tuple[str, str]:
        """Publish markdown report to S3."""
        date_str = date.strftime("%Y-%m-%d")
        filename = f"ai-weekly-{date_str}.md"

        # Upload to latest/ directory
        latest_key = f"latest/{filename}"
        self._upload_file(latest_key, markdown_content, "text/markdown")

        # Upload to versioned directory
        versioned_key = f"reports/{date.year}/{date.month:02d}/{filename}"
        self._upload_file(versioned_key, markdown_content, "text/markdown")

        latest_url = f"s3://{self.bucket_name}/{latest_key}"
        versioned_url = f"s3://{self.bucket_name}/{versioned_key}"

        logger.info(f"Published report to {latest_url} and {versioned_url}")
        return latest_url, versioned_url

    def save_paper_data(self, papers: List[Paper], date: datetime) -> str:
        """Save paper data as parquet for historical analysis."""
        # Convert papers to DataFrame
        paper_data = []
        for paper in papers:
            data = paper.to_dict()
            # Add processing date
            data["processed_date"] = date.isoformat()
            paper_data.append(data)

        df = pd.DataFrame(paper_data)

        # Convert to parquet bytes
        parquet_buffer = df.to_parquet(index=False)

        # Save to S3
        date_str = date.strftime("%Y-%m-%d")
        key = f"history/papers-{date_str}.parquet"

        self._upload_file(key, parquet_buffer, "application/octet-stream")

        url = f"s3://{self.bucket_name}/{key}"
        logger.info(f"Saved paper data to {url}")
        return url

    def _upload_file(self, key: str, content: Union[str, bytes], content_type: str):
        """Upload file to S3."""
        try:
            if isinstance(content, str):
                body = content.encode("utf-8")
            else:
                body = content

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )

        except ClientError as e:
            logger.error(f"Failed to upload {key} to S3: {e}")
            raise


class SESPublisher:
    """Sends reports via AWS SES."""

    def __init__(self, sender_email: str):
        self.sender_email = sender_email
        self.ses_client = boto3.client("ses")

    def send_report(
        self, markdown_content: str, recipients: List[str], date: datetime
    ) -> bool:
        """Send report via email."""
        if not recipients:
            logger.info("No recipients configured, skipping email")
            return True

        date_str = date.strftime("%Y-%m-%d")
        subject = f"AI Research Weekly - {date_str}"

        # Convert markdown to simple text for email
        text_content = self._markdown_to_text(markdown_content)

        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={"ToAddresses": recipients},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": text_content, "Charset": "UTF-8"}},
                },
            )

            message_id = response["MessageId"]
            logger.info(f"Email sent successfully. Message ID: {message_id}")
            return True

        except ClientError as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _markdown_to_text(self, markdown: str) -> str:
        """Simple markdown to text conversion."""
        # Remove front matter
        lines = markdown.split("\n")
        if lines[0] == "---":
            # Find end of front matter
            end_idx = 1
            while end_idx < len(lines) and lines[end_idx] != "---":
                end_idx += 1
            lines = lines[end_idx + 1 :]

        text = "\n".join(lines)

        # Simple markdown cleanup
        text = text.replace("**", "")
        text = text.replace("### ", "")
        text = text.replace("## ", "")
        text = text.replace("# ", "")

        # Remove links but keep text
        import re

        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        return text.strip()


def publish_report(
    papers: List[Paper],
    intro: str,
    bucket_name: str,
    sender_email: Optional[str] = None,
    recipients: Optional[List[str]] = None,
    date: Optional[datetime] = None,
) -> dict:
    """Main publishing function."""

    if date is None:
        date = datetime.now()

    logger.info(f"Publishing report for {len(papers)} papers")

    # Generate markdown
    generator = MarkdownGenerator()
    markdown_content = generator.generate_report(papers, intro, date)

    # Publish to S3
    s3_publisher = S3Publisher(bucket_name)
    latest_url, versioned_url = s3_publisher.publish_report(markdown_content, date)

    # Save historical data
    data_url = s3_publisher.save_paper_data(papers, date)

    result = {
        "latest_url": latest_url,
        "versioned_url": versioned_url,
        "data_url": data_url,
        "email_sent": False,
    }

    # Send email if configured
    if sender_email and recipients:
        ses_publisher = SESPublisher(sender_email)
        email_sent = ses_publisher.send_report(markdown_content, recipients, date)
        result["email_sent"] = email_sent

    logger.info("Publishing completed successfully")
    return result
