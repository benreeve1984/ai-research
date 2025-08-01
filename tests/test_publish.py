"""Tests for report publishing functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.ai_weekly.publish import (
    MarkdownGenerator,
    S3Publisher,
    SESPublisher,
    publish_report
)


class TestMarkdownGenerator:
    """Test markdown report generation."""

    def test_generate_report_basic(self, sample_papers):
        """Test basic markdown report generation."""
        # Add summaries to papers
        for i, paper in enumerate(sample_papers):
            paper.summary = f"Summary for paper {i+1}"
        
        intro = "This week's AI research highlights..."
        date = datetime(2024, 1, 15)
        
        generator = MarkdownGenerator()
        markdown = generator.generate_report(sample_papers, intro, date)
        
        # Check header
        assert "# AI Research Weekly - 2024-01-15" in markdown
        assert "This week's AI research highlights..." in markdown
        assert "## Featured Papers" in markdown
        
        # Check paper sections
        for i, paper in enumerate(sample_papers):
            assert f"### {i+1}. {paper.title}" in markdown
            assert f"Summary for paper {i+1}" in markdown
            assert f"**Authors:** {', '.join(paper.authors)}" in markdown

    def test_generate_report_with_github(self, sample_paper):
        """Test markdown generation with GitHub links."""
        sample_paper.summary = "Test summary"
        sample_paper.github_url = "https://github.com/test/repo"
        sample_paper.github_stars = 150
        
        generator = MarkdownGenerator()
        markdown = generator.generate_report([sample_paper], "Intro", datetime.now())
        
        assert "GitHub" in markdown

    def test_generate_report_front_matter(self, sample_paper):
        """Test markdown front matter generation."""
        sample_paper.summary = "Test summary"
        date = datetime(2024, 1, 15)
        
        generator = MarkdownGenerator()
        markdown = generator.generate_report([sample_paper], "Intro", date)
        
        assert "---" in markdown
        assert 'title: "AI Research Weekly - 2024-01-15"' in markdown
        assert 'date: "2024-01-15T00:00:00"' in markdown


class TestS3Publisher:
    """Test S3 publishing functionality."""

    @patch('boto3.client')
    def test_publish_report_success(self, mock_boto_client):
        """Test successful S3 report publishing."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.put_object.return_value = {}
        
        publisher = S3Publisher("test-bucket")
        date = datetime(2024, 1, 15)
        
        latest_url, versioned_url = publisher.publish_report("# Test Report", date)
        
        # Check S3 uploads
        assert mock_s3_client.put_object.call_count == 2  # latest + versioned
        
        # Check URLs
        assert "s3://test-bucket/latest/" in latest_url
        assert "s3://test-bucket/reports/2024/01/" in versioned_url

    @patch('boto3.client')
    def test_save_paper_data(self, mock_boto_client, sample_papers):
        """Test saving paper data as parquet."""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.put_object.return_value = {}
        
        publisher = S3Publisher("test-bucket")
        date = datetime(2024, 1, 15)
        
        data_url = publisher.save_paper_data(sample_papers, date)
        
        # Check upload was called
        mock_s3_client.put_object.assert_called_once()
        assert "s3://test-bucket/history/papers-2024-01-15.parquet" in data_url


class TestSESPublisher:
    """Test SES email functionality."""

    @patch('boto3.client')
    def test_send_report_success(self, mock_boto_client):
        """Test successful email sending."""
        # Mock SES client
        mock_ses_client = Mock()
        mock_boto_client.return_value = mock_ses_client
        mock_ses_client.send_email.return_value = {"MessageId": "test-message-id"}
        
        publisher = SESPublisher("sender@example.com")
        date = datetime(2024, 1, 15)
        
        result = publisher.send_report(
            "# Test Report",
            ["user1@example.com", "user2@example.com"],
            date
        )
        
        assert result is True
        mock_ses_client.send_email.assert_called_once()
        
        # Check email parameters
        call_args = mock_ses_client.send_email.call_args[1]
        assert call_args["Source"] == "sender@example.com"
        assert call_args["Destination"]["ToAddresses"] == ["user1@example.com", "user2@example.com"]

    def test_send_report_no_recipients(self):
        """Test email sending with no recipients."""
        publisher = SESPublisher("sender@example.com")
        
        result = publisher.send_report("# Test Report", [], datetime.now())
        
        assert result is True  # Should succeed but skip sending

    def test_markdown_to_text(self):
        """Test markdown to text conversion."""
        publisher = SESPublisher("sender@example.com")
        
        markdown = """---
title: Test
---

# Title

## Section

**Bold text** and [link](http://example.com)"""
        
        text = publisher._markdown_to_text(markdown)
        
        assert "---" not in text
        assert "title: Test" not in text
        assert "Title" in text
        assert "Section" in text
        assert "Bold text" in text
        assert "link" in text
        assert "http://example.com" not in text


class TestPublishReport:
    """Test main publish function."""

    @patch('src.ai_weekly.publish.S3Publisher')
    @patch('src.ai_weekly.publish.MarkdownGenerator')
    def test_publish_report_success(self, mock_generator, mock_s3_publisher, sample_papers):
        """Test successful report publishing."""
        # Mock generator
        mock_gen_instance = Mock()
        mock_generator.return_value = mock_gen_instance
        mock_gen_instance.generate_report.return_value = "# Test Report"
        
        # Mock S3 publisher
        mock_s3_instance = Mock()
        mock_s3_publisher.return_value = mock_s3_instance
        mock_s3_instance.publish_report.return_value = ("latest_url", "versioned_url")
        mock_s3_instance.save_paper_data.return_value = "data_url"
        
        # Add summaries to papers
        for paper in sample_papers:
            paper.summary = "Test summary"
        
        result = publish_report(
            papers=sample_papers,
            intro="Test intro",
            bucket_name="test-bucket"
        )
        
        # Check result
        assert "latest_url" in result
        assert "versioned_url" in result
        assert "data_url" in result
        assert result["email_sent"] is False

    @patch('src.ai_weekly.publish.SESPublisher')
    @patch('src.ai_weekly.publish.S3Publisher')
    @patch('src.ai_weekly.publish.MarkdownGenerator')
    def test_publish_report_with_email(self, mock_generator, mock_s3_publisher, mock_ses_publisher, sample_papers):
        """Test report publishing with email notifications."""
        # Mock generator
        mock_gen_instance = Mock()
        mock_generator.return_value = mock_gen_instance
        mock_gen_instance.generate_report.return_value = "# Test Report"
        
        # Mock S3 publisher
        mock_s3_instance = Mock()
        mock_s3_publisher.return_value = mock_s3_instance
        mock_s3_instance.publish_report.return_value = ("latest_url", "versioned_url")
        mock_s3_instance.save_paper_data.return_value = "data_url"
        
        # Mock SES publisher
        mock_ses_instance = Mock()
        mock_ses_publisher.return_value = mock_ses_instance
        mock_ses_instance.send_report.return_value = True
        
        # Add summaries to papers
        for paper in sample_papers:
            paper.summary = "Test summary"
        
        result = publish_report(
            papers=sample_papers,
            intro="Test intro",
            bucket_name="test-bucket",
            sender_email="sender@example.com",
            recipients=["user@example.com"]
        )
        
        assert result["email_sent"] is True
        mock_ses_instance.send_report.assert_called_once()


