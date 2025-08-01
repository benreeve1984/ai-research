"""Tests for Lambda handler functionality."""

import json
import pytest
from unittest.mock import Mock, patch
from src.ai_weekly.lambda_handler import lambda_handler, run_pipeline


class TestLambdaHandler:
    """Test Lambda handler function."""
    
    def test_lambda_handler_success(self, sample_papers, mock_config):
        """Test successful Lambda execution."""
        # Mock all the pipeline steps
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.enrich_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.rank_papers', return_value=sample_papers[:3]), \
             patch('src.ai_weekly.lambda_handler.summarize_papers', return_value=(sample_papers[:3], "Test intro")), \
             patch('src.ai_weekly.lambda_handler.publish_report', return_value={
                 'latest_url': 's3://test/latest.md',
                 'versioned_url': 's3://test/versioned.md',
                 'data_url': 's3://test/data.parquet',
                 'email_sent': True
             }):
            
            # Mock Lambda context
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            event = {"source": "test"}
            
            result = lambda_handler(event, context)
            
            # Check response structure
            assert result['statusCode'] == 200
            
            body = json.loads(result['body'])
            assert body['status'] == 'completed'
            assert body['papers_harvested'] == len(sample_papers)
            assert body['papers_published'] == 3
            assert 'execution_time_seconds' in body
            assert 'publish_result' in body
    
    def test_lambda_handler_no_papers(self, mock_config):
        """Test Lambda execution when no papers are found."""
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', return_value=[]):
            
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            result = lambda_handler({}, context)
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['status'] == 'completed'
            assert body['papers_count'] == 0
            assert 'No papers found' in body['message']
    
    def test_lambda_handler_config_error(self):
        """Test Lambda execution with configuration error."""
        with patch('src.ai_weekly.lambda_handler.load_config', side_effect=ValueError("Config error")):
            
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            result = lambda_handler({}, context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert body['status'] == 'error'
            assert 'Config error' in body['message']
    
    def test_lambda_handler_harvest_error(self, mock_config):
        """Test Lambda execution with harvesting error."""
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', side_effect=Exception("Harvest error")):
            
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            result = lambda_handler({}, context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert body['status'] == 'error'
            assert 'Harvest error' in body['message']
    
    def test_lambda_handler_openai_backend(self, sample_papers, mock_config):
        """Test Lambda execution with OpenAI backend."""
        mock_config.llm_backend = "openai"
        mock_config.openai_api_key = "test-openai-key"
        
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.enrich_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.rank_papers', return_value=sample_papers[:3]), \
             patch('src.ai_weekly.lambda_handler.summarize_papers') as mock_summarize, \
             patch('src.ai_weekly.lambda_handler.publish_report', return_value={}):
            
            mock_summarize.return_value = (sample_papers[:3], "Test intro")
            
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            result = lambda_handler({}, context)
            
            # Check that summarize_papers was called with OpenAI parameters
            mock_summarize.assert_called_once_with(
                papers=sample_papers[:3],
                backend="openai",
                api_key="test-openai-key",
                model="gpt-4o-mini"
            )
            
            assert result['statusCode'] == 200
    
    def test_lambda_handler_anthropic_backend(self, sample_papers, mock_config):
        """Test Lambda execution with Anthropic backend."""
        mock_config.llm_backend = "anthropic"
        mock_config.anthropic_api_key = "test-anthropic-key"
        
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.enrich_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.rank_papers', return_value=sample_papers[:3]), \
             patch('src.ai_weekly.lambda_handler.summarize_papers') as mock_summarize, \
             patch('src.ai_weekly.lambda_handler.publish_report', return_value={}):
            
            mock_summarize.return_value = (sample_papers[:3], "Test intro")
            
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            result = lambda_handler({}, context)
            
            # Check that summarize_papers was called with Anthropic parameters
            mock_summarize.assert_called_once_with(
                papers=sample_papers[:3],
                backend="anthropic",
                api_key="test-anthropic-key",
                model="gpt-4o-mini"
            )
            
            assert result['statusCode'] == 200
    
    def test_lambda_handler_unsupported_backend(self, sample_papers, mock_config):
        """Test Lambda execution with unsupported LLM backend."""
        mock_config.llm_backend = "unsupported"
        
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.enrich_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.rank_papers', return_value=sample_papers[:3]):
            
            context = Mock()
            context.aws_request_id = "test-request-id"
            
            result = lambda_handler({}, context)
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert body['status'] == 'error'
            assert 'Unsupported LLM backend' in body['message']


class TestRunPipeline:
    """Test local pipeline runner."""
    
    def test_run_pipeline_success(self, sample_papers, mock_config):
        """Test successful local pipeline execution."""
        with patch('src.ai_weekly.lambda_handler.load_config', return_value=mock_config), \
             patch('src.ai_weekly.lambda_handler.harvest_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.enrich_papers', return_value=sample_papers), \
             patch('src.ai_weekly.lambda_handler.rank_papers', return_value=sample_papers[:3]), \
             patch('src.ai_weekly.lambda_handler.summarize_papers', return_value=(sample_papers[:3], "Test intro")), \
             patch('src.ai_weekly.lambda_handler.publish_report', return_value={}):
            
            result = run_pipeline()
            
            assert result['statusCode'] == 200
            body = json.loads(result['body'])
            assert body['status'] == 'completed'
    
    def test_run_pipeline_error(self, mock_config):
        """Test local pipeline execution with error."""
        with patch('src.ai_weekly.lambda_handler.load_config', side_effect=Exception("Test error")):
            
            result = run_pipeline()
            
            assert result['statusCode'] == 500
            body = json.loads(result['body'])
            assert body['status'] == 'error'