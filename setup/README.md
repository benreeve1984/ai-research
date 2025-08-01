# 🚀 AI Research Weekly - CI/CD Setup

This directory contains all the tools and scripts needed to set up seamless GitHub → AWS CI/CD for the AI Research Weekly pipeline.

## 📁 Files Overview

| File | Description |
|------|-------------|
| `setup-script.sh` | **🎯 One-click automated setup** - Recommended for most users |
| `manual-setup-guide.md` | **📋 Step-by-step manual setup** - For custom configurations |
| `github-oidc-stack.yaml` | **☁️ CloudFormation template** - AWS infrastructure as code |
| `test-pipeline.sh` | **🧪 Pipeline testing script** - Verify everything works |

## 🎯 Quick Start (Recommended)

### Prerequisites
- AWS CLI installed and configured
- GitHub CLI installed (optional but recommended)
- Your GitHub repository created

### 1. Configure the Setup Script

Edit `setup-script.sh` and update these variables:

```bash
GITHUB_ORG="your-github-username"  # Your GitHub username/org
GITHUB_REPO="ai-research-weekly"   # Your repository name
AWS_REGION="us-east-1"             # Your preferred AWS region
```

### 2. Run the Automated Setup

```bash
cd setup/
./setup-script.sh
```

The script will:
- ✅ Create GitHub OIDC provider in AWS
- ✅ Create IAM role with necessary permissions
- ✅ Set up S3 bucket for reports
- ✅ Create Secrets Manager secret for API keys
- ✅ Configure GitHub repository secrets

### 3. Test the Pipeline

```bash
./test-pipeline.sh
```

### 4. Deploy and Test

```bash
# Go back to project root
cd ..

# Deploy using SAM
sam build --use-container
sam deploy --guided

# Test the deployed pipeline
./setup/test-pipeline.sh
```

## 🔧 Manual Setup

If you prefer manual setup or need custom configuration, follow the detailed guide in `manual-setup-guide.md`.

## 📊 What Gets Created

### AWS Resources
- **OIDC Identity Provider**: Allows GitHub Actions to assume AWS roles
- **IAM Role**: `ai-weekly-github-actions-role` with deployment permissions
- **S3 Bucket**: Stores generated reports and historical data
- **Secrets Manager Secret**: Stores API keys securely

### GitHub Secrets
- `AWS_ROLE_TO_ASSUME`: IAM role ARN for GitHub Actions
- `REPORT_BUCKET`: S3 bucket name for reports
- `SECRET_NAME`: Secrets Manager secret name
- `LLM_BACKEND`: OpenAI or Anthropic (`openai`/`anthropic`)
- `LLM_MODEL`: Model name (e.g., `gpt-4o-mini`)
- `SES_SENDER`: Email sender (optional)
- `SUBSCRIBERS`: Email subscribers (optional)

## 🔒 Security Features

- **OIDC Authentication**: No long-lived AWS credentials stored in GitHub
- **Least Privilege**: IAM role has minimum required permissions
- **Encrypted Storage**: S3 bucket uses AES-256 encryption
- **Secret Management**: API keys stored in AWS Secrets Manager
- **Branch Protection**: Role can only be assumed from main branch

## 🧪 Testing and Validation

### Automated Tests
The CI/CD pipeline includes:
- **Unit Tests**: pytest with 80%+ coverage requirement
- **Linting**: black, flake8, mypy for code quality
- **Security Scanning**: bandit and safety for vulnerability detection
- **Deployment Testing**: SAM build and deploy validation

### Manual Testing
Use the test script to verify:
```bash
./test-pipeline.sh
```

This checks:
- ✅ CloudFormation stack status
- ✅ Lambda function deployment
- ✅ Function execution and logs
- ✅ S3 bucket accessibility
- ✅ EventBridge schedule configuration

## 🔄 CI/CD Workflow

### Trigger Events
- **Push to main**: Runs tests → deploys to AWS
- **Pull requests**: Runs tests and security scans
- **Schedule**: Runs every Sunday (manual Lambda invocation)
- **Manual**: GitHub Actions can be triggered manually

### Workflow Steps
1. **Test Job**:
   - Install dependencies
   - Run linting (black, flake8, mypy)
   - Execute tests with coverage
   - Upload coverage reports

2. **Deploy Job** (main branch only):
   - Configure AWS credentials via OIDC
   - Build SAM application in container
   - Deploy to AWS with parameters
   - Show deployment outputs

3. **Security Scan** (PRs only):
   - Run bandit security analysis
   - Check for known vulnerabilities with safety
   - Upload security reports

## 📧 Optional: Email Notifications

To enable email notifications:

1. **Verify sender email in SES**:
   ```bash
   aws ses verify-email-identity --email-address your-email@example.com
   ```

2. **Add email secrets to GitHub**:
   - `SES_SENDER`: your-verified-email@example.com
   - `SUBSCRIBERS`: email1@example.com,email2@example.com

3. **Move out of SES sandbox** (if sending to unverified emails):
   - Request production access in AWS SES Console

## 🛠️ Customization

### Modify Deployment Parameters
Edit the SAM deploy command in `.github/workflows/ci-cd.yml`:

```yaml
sam deploy \
  --parameter-overrides \
    ReportBucket=${{ secrets.REPORT_BUCKET }} \
    LLMBackend=${{ secrets.LLM_BACKEND }} \
    # Add your custom parameters here
```

### Add Environment Variables
Update the SAM template `template.yaml`:

```yaml
Environment:
  Variables:
    CUSTOM_VARIABLE: !Ref CustomParameter
```

### Modify IAM Permissions
Edit `github-oidc-stack.yaml` to add/remove permissions:

```yaml
- Effect: Allow
  Action:
    - your:custom:permission
  Resource: '*'
```

## 🐛 Troubleshooting

### Common Issues

1. **GitHub Actions Permission Denied**
   - Check IAM role trust policy has correct repository
   - Verify OIDC provider thumbprints are current

2. **SAM Deploy Fails**
   - Ensure IAM role has CloudFormation permissions
   - Check S3 bucket permissions for SAM artifacts

3. **Lambda Function Not Found**
   - Verify SAM template function name
   - Check CloudFormation stack deployment status

4. **API Keys Not Accessible**
   - Ensure Secrets Manager secret exists
   - Verify Lambda execution role has SecretsManager permissions

### Debug Commands

```bash
# Check GitHub Actions role
aws iam get-role --role-name ai-weekly-github-actions-role

# List CloudFormation stacks
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Check Lambda function
aws lambda get-function --function-name ai-research-weekly

# Test secret access
aws secretsmanager get-secret-value --secret-id ai-weekly/api-keys
```

## 📊 Monitoring and Maintenance

### CloudWatch Monitoring
- Lambda function metrics and logs
- S3 bucket access patterns
- EventBridge rule execution

### Cost Optimization
- S3 lifecycle policies for old versions
- Lambda memory optimization
- CloudWatch log retention policies

### Security Maintenance
- Rotate API keys in Secrets Manager
- Review IAM policies regularly
- Monitor CloudTrail for access patterns

## 🎉 Success Checklist

After setup, verify:
- [ ] GitHub Actions workflow runs successfully
- [ ] Lambda function deploys and executes
- [ ] Reports are published to S3
- [ ] EventBridge schedule is active
- [ ] Email notifications work (if configured)
- [ ] CloudWatch logs are accessible

Your seamless GitHub → AWS CI/CD pipeline is now ready! 🚀