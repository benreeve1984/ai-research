# AI Research Weekly

A serverless pipeline that automatically generates weekly AI research digests by harvesting, enriching, ranking, and summarizing recent academic papers from arXiv and PapersWithCode.

## 🚀 Features

- **Automated Paper Harvesting**: Collects papers from arXiv (cs.AI, cs.LG, cs.CL, cs.CV) and PapersWithCode trending papers
- **Intelligent Enrichment**: Enhances papers with Semantic Scholar citation counts, SPECTER2 embeddings, and GitHub stars
- **Smart Ranking**: Ranks papers using a weighted scoring algorithm combining citations, GitHub popularity, and social buzz
- **AI-Powered Summarization**: Generates concise summaries using OpenAI GPT or Anthropic Claude
- **Multi-format Publishing**: Outputs markdown reports to S3 with email distribution via AWS SES
- **Serverless Architecture**: Runs entirely on AWS Lambda with EventBridge scheduling

## 📋 Requirements

- AWS Account with appropriate permissions
- Python 3.12+
- AWS SAM CLI
- API keys for external services (stored in AWS Secrets Manager)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│   AWS Lambda     │───▶│   S3 Bucket     │
│   (Schedule)    │    │   (Pipeline)     │    │   (Reports)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Secrets Manager  │    │   AWS SES       │
                       │   (API Keys)     │    │   (Email)       │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd ai-research-weekly
pip install -r requirements.txt
```

### 2. Set up AWS Secrets Manager

Create a secret in AWS Secrets Manager with your API keys:

```json
{
  "OPENAI_API_KEY": "your-openai-key",
  "ANTHROPIC_API_KEY": "your-anthropic-key", 
  "SEMANTIC_SCHOLAR_API_KEY": "your-s2-key",
  "GITHUB_TOKEN": "your-github-token"
}
```

### 3. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `AWS_ROLE_TO_ASSUME`: ARN of the IAM role for GitHub Actions
- `REPORT_BUCKET`: S3 bucket name for storing reports
- `SECRET_NAME`: Name of the Secrets Manager secret
- `LLM_BACKEND`: "openai" or "anthropic" 
- `LLM_MODEL`: Model name (e.g., "gpt-4o-mini")
- `SES_SENDER`: Verified SES sender email (optional)
- `SUBSCRIBERS`: Comma-separated subscriber emails (optional)

### 4. Deploy with SAM

```bash
# Build the application
sam build --use-container

# Deploy to AWS
sam deploy --guided
```

### 5. Test Locally

```bash
# Set environment variables
export REPORT_BUCKET=your-bucket-name
export SECRET_NAME=your-secret-name
export LLM_BACKEND=openai

# Run the pipeline locally
python -m src.ai_weekly.lambda_handler
```

## 📊 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REPORT_BUCKET` | S3 bucket for reports | Required |
| `SECRET_NAME` | Secrets Manager secret name | Required |
| `LLM_BACKEND` | LLM provider (openai/anthropic) | openai |
| `LLM_MODEL` | Model to use | gpt-4o-mini |
| `SES_SENDER` | SES sender email | None |
| `SUBSCRIBERS` | Comma-separated emails | None |
| `DAYS_LOOKBACK` | Days to look back for papers | 7 |
| `TOP_K_PAPERS` | Number of top papers to include | 10 |

### Ranking Algorithm

Papers are scored using the formula:
```
score = 0.5 × log(citations + 1) + 0.3 × normalized_github_stars + 0.2 × social_buzz
```

Where:
- `citations`: Citation count from Semantic Scholar
- `normalized_github_stars`: Min-max normalized GitHub stars (0-1)
- `social_buzz`: Currently always 0 (placeholder for future social metrics)

## 🧪 Testing

Run the full test suite:

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test files
pytest tests/test_harvest.py -v

# Run with coverage threshold
pytest --cov=src --cov-fail-under=80
```

## 📈 Monitoring

The deployment includes:
- CloudWatch Dashboard for Lambda metrics
- Structured JSON logging for debugging
- CloudWatch alarms for errors and timeouts
- S3 lifecycle policies for cost optimization

Access the dashboard at:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=AI-Research-Weekly
```

## 🔧 Development

### Local Development

1. Create a `.env` file with your API keys:
```bash
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
SEMANTIC_SCHOLAR_API_KEY=your-key
GITHUB_TOKEN=your-token
REPORT_BUCKET=test-bucket
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

3. Run the pipeline locally:
```bash
python -m src.ai_weekly.lambda_handler
```

### Adding New Paper Sources

To add new paper sources:

1. Create a new harvester class in `src/ai_weekly/harvest.py`
2. Implement the `harvest()` method returning `List[Paper]`
3. Add the harvester to the `harvest_papers()` function
4. Add corresponding tests in `tests/test_harvest.py`

### Custom Ranking Algorithms

Modify the scoring in `src/ai_weekly/rank.py`:

```python
def calculate_paper_score(paper: Paper, **weights) -> float:
    # Your custom scoring logic here
    return score
```

## 📁 Project Structure

```
.
├── README.md
├── requirements.txt
├── template.yaml                  # SAM infrastructure
├── src/ai_weekly/
│   ├── __init__.py
│   ├── config.py                  # Environment configuration  
│   ├── harvest.py                 # arXiv & PapersWithCode harvesting
│   ├── enrich.py                  # Semantic Scholar & GitHub enrichment
│   ├── rank.py                    # Paper ranking logic
│   ├── summarise.py               # LLM-based summarization
│   ├── publish.py                 # S3 & SES publishing
│   └── lambda_handler.py          # Main Lambda handler
├── tests/                         # Pytest test suite
│   ├── conftest.py
│   ├── test_harvest.py
│   ├── test_rank.py
│   ├── test_summarise.py
│   └── test_lambda_handler.py
└── .github/workflows/
    └── ci-cd.yml                  # GitHub Actions CI/CD
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure tests pass (`pytest --cov=src --cov-fail-under=80`)
5. Run linting (`black src/ tests/ && flake8 src/ tests/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔍 Troubleshooting

### Common Issues

**Lambda timeout errors:**
- Increase timeout in `template.yaml` (max 15 minutes)
- Reduce the number of papers processed
- Optimize API calls with better rate limiting

**API rate limiting:**
- Add delays between requests in enrichment modules
- Use API keys to increase rate limits
- Implement exponential backoff

**S3 permissions errors:**
- Verify the Lambda execution role has S3 permissions
- Check bucket name and region configuration
- Ensure bucket exists and is accessible

**Memory errors:**
- Increase Lambda memory allocation in `template.yaml`
- Process papers in smaller batches
- Optimize data structures for memory usage

### Debug Logging

Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
```

### Manual Testing

Test individual components:

```bash
# Test paper harvesting
python -c "from src.ai_weekly.harvest import harvest_papers; print(len(harvest_papers(['cs.AI'])))"

# Test ranking
python -c "from src.ai_weekly.rank import rank_papers; from src.ai_weekly.harvest import harvest_papers; papers=harvest_papers(['cs.AI']); print(len(rank_papers(papers, 5)))"
```

## 📊 Metrics and Monitoring

Key metrics tracked:
- Papers harvested per run
- Success/failure rates
- Processing time per stage
- API response times
- S3 upload success rates
- Email delivery rates

Access logs:
```bash
aws logs tail /aws/lambda/ai-research-weekly --follow
```