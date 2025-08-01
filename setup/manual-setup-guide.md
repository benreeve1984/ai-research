# Manual GitHub → AWS CI/CD Setup Guide

If you prefer to set up the CI/CD pipeline manually or the automated script doesn't work for your setup, follow these step-by-step instructions.

## Prerequisites

- AWS CLI installed and configured
- GitHub CLI installed (optional, for automatic secret setting)
- AWS Account with appropriate permissions
- GitHub repository for the project

## Step 1: Create GitHub OIDC Identity Provider

### Using AWS Console:

1. Go to **IAM → Identity providers → Add provider**
2. Select **OpenID Connect**
3. Set the following values:
   - **Provider URL**: `https://token.actions.githubusercontent.com`
   - **Audience**: `sts.amazonaws.com`
   - **Thumbprints**: 
     - `6938fd4d98bab03faadb97b34396831e3780aea1`
     - `1c58a3a8518e8759bf075b76b750d4f2df264fcd`

### Using AWS CLI:

```bash
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 1c58a3a8518e8759bf075b76b750d4f2df264fcd
```

## Step 2: Create IAM Role for GitHub Actions

### Create Trust Policy

Create a file `github-trust-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": [
                        "repo:YOUR_GITHUB_ORG/YOUR_REPO:ref:refs/heads/main",
                        "repo:YOUR_GITHUB_ORG/YOUR_REPO:pull_request"
                    ]
                }
            }
        }
    ]
}
```

Replace `YOUR_ACCOUNT_ID`, `YOUR_GITHUB_ORG`, and `YOUR_REPO` with your actual values.

### Create Permissions Policy

Create a file `github-permissions-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "s3:*",
                "lambda:*",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:PassRole",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:GetRolePolicy",
                "events:*",
                "logs:*",
                "cloudwatch:*",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "ses:SendEmail",
                "ses:SendRawEmail",
                "ses:VerifyEmailIdentity",
                "ses:ListIdentities"
            ],
            "Resource": "*"
        }
    ]
}
```

### Create the Role

```bash
# Create the role
aws iam create-role \
    --role-name ai-weekly-github-actions-role \
    --assume-role-policy-document file://github-trust-policy.json

# Attach the permissions policy
aws iam put-role-policy \
    --role-name ai-weekly-github-actions-role \
    --policy-name SAMDeploymentPolicy \
    --policy-document file://github-permissions-policy.json

# Get the role ARN (save this for later)
aws iam get-role \
    --role-name ai-weekly-github-actions-role \
    --query 'Role.Arn' \
    --output text
```

## Step 3: Create S3 Bucket for Reports

```bash
# Set your bucket name (must be globally unique)
REPORT_BUCKET="ai-research-weekly-reports-$(date +%s)"

# Create bucket
aws s3 mb s3://$REPORT_BUCKET --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $REPORT_BUCKET \
    --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket $REPORT_BUCKET \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }'

# Block public access
aws s3api put-public-access-block \
    --bucket $REPORT_BUCKET \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Step 4: Create AWS Secrets Manager Secret

```bash
# Create the secret with your API keys
aws secretsmanager create-secret \
    --name "ai-weekly/api-keys" \
    --description "API keys for AI Research Weekly pipeline" \
    --secret-string '{
        "OPENAI_API_KEY": "your-openai-key",
        "ANTHROPIC_API_KEY": "your-anthropic-key",
        "SEMANTIC_SCHOLAR_API_KEY": "your-s2-key",
        "GITHUB_TOKEN": "your-github-token"
    }'
```

## Step 5: Set GitHub Repository Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

Add the following **Repository secrets**:

### Required Secrets:
- **AWS_ROLE_TO_ASSUME**: `arn:aws:iam::YOUR_ACCOUNT_ID:role/ai-weekly-github-actions-role`
- **REPORT_BUCKET**: `your-bucket-name`
- **SECRET_NAME**: `ai-weekly/api-keys`
- **LLM_BACKEND**: `openai` (or `anthropic`)
- **LLM_MODEL**: `gpt-4o-mini`

### Optional Secrets (for email notifications):
- **SES_SENDER**: `your-verified-email@example.com`
- **SUBSCRIBERS**: `email1@example.com,email2@example.com`

### Using GitHub CLI:

```bash
# Set required secrets
gh secret set AWS_ROLE_TO_ASSUME --body "arn:aws:iam::YOUR_ACCOUNT_ID:role/ai-weekly-github-actions-role"
gh secret set REPORT_BUCKET --body "$REPORT_BUCKET"
gh secret set SECRET_NAME --body "ai-weekly/api-keys"
gh secret set LLM_BACKEND --body "openai"
gh secret set LLM_MODEL --body "gpt-4o-mini"

# Optional secrets
gh secret set SES_SENDER --body "your-email@example.com"
gh secret set SUBSCRIBERS --body "subscriber1@example.com,subscriber2@example.com"
```

## Step 6: Test the Setup

1. **Push to main branch** to trigger the CI/CD pipeline
2. **Check GitHub Actions** at `https://github.com/YOUR_ORG/YOUR_REPO/actions`
3. **Monitor CloudWatch logs** for the Lambda function
4. **Verify S3 bucket** has the reports

### Manual Lambda Test:

```bash
# After deployment, test the Lambda function
aws lambda invoke \
    --function-name ai-research-weekly \
    --payload '{"source": "manual-test"}' \
    response.json

# Check the response
cat response.json | jq '.'
```

## Optional: Set up SES for Email Notifications

### 1. Verify Sender Email:

```bash
aws ses verify-email-identity --email-address your-email@example.com
```

### 2. Check Verification Status:

```bash
aws ses get-identity-verification-attributes --identities your-email@example.com
```

### 3. Request Production Access (if needed):

If you want to send emails to unverified addresses, request to move out of the SES sandbox in the AWS Console.

## Troubleshooting

### Common Issues:

1. **Permission Denied**: Ensure your IAM role has all necessary permissions
2. **Bucket Already Exists**: Choose a unique bucket name
3. **Secret Not Found**: Verify the secret name matches exactly
4. **GitHub Actions Failing**: Check the role ARN and repository name in trust policy

### Debug Commands:

```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name ai-research-weekly

# Check Lambda logs
aws logs tail /aws/lambda/ai-research-weekly --follow

# List S3 bucket contents
aws s3 ls s3://your-bucket-name --recursive

# Test secret access
aws secretsmanager get-secret-value --secret-id ai-weekly/api-keys
```

## Security Best Practices

1. **Least Privilege**: Only grant necessary permissions to the GitHub Actions role
2. **Secrets Rotation**: Regularly rotate API keys stored in Secrets Manager
3. **Monitoring**: Set up CloudWatch alarms for failed executions
4. **Audit**: Regularly review IAM policies and access patterns

## Cost Optimization

1. **S3 Lifecycle**: Set up lifecycle policies to delete old versions
2. **Lambda Memory**: Adjust memory allocation based on actual usage
3. **CloudWatch Logs**: Set retention periods for log groups
4. **Reserved Capacity**: Consider reserved capacity for predictable workloads

Your GitHub → AWS CI/CD pipeline is now ready! 🚀