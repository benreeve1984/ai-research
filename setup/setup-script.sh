#!/bin/bash

# AI Research Weekly - GitHub CI/CD Setup Script
# This script sets up the complete CI/CD pipeline for GitHub → AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - UPDATE THESE VALUES
GITHUB_ORG="benreeve1984"  # Change this to your GitHub username/org
GITHUB_REPO="ai-research"   # Change this to your repo name
AWS_REGION="us-east-1"             # OIDC providers must be created in us-east-1
REPORT_BUCKET="ai-research-weekly-reports-$(date +%s)"  # Unique bucket name
SECRET_NAME="ai-weekly/api-keys"

echo -e "${BLUE}🚀 Setting up AI Research Weekly CI/CD Pipeline${NC}"
echo -e "${BLUE}================================================${NC}\n"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if AWS is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Check GitHub CLI (optional but recommended)
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI not found. You'll need to set secrets manually.${NC}"
    GH_CLI_AVAILABLE=false
else
    GH_CLI_AVAILABLE=true
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}\n"

# Step 1: Deploy GitHub OIDC CloudFormation stack
echo -e "${BLUE}🔐 Step 1: Setting up GitHub OIDC Provider and IAM Role${NC}"

STACK_NAME="ai-weekly-github-oidc"

aws cloudformation deploy \
    --template-file github-oidc-stack.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        GitHubOrg=$GITHUB_ORG \
        GitHubRepo=$GITHUB_REPO \
        ReportBucketName=$REPORT_BUCKET \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $AWS_REGION

# Get the role ARN
GITHUB_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`GitHubActionsRoleArn`].OutputValue' \
    --output text)

echo -e "${GREEN}✅ GitHub OIDC setup completed${NC}"
echo -e "${GREEN}   Role ARN: $GITHUB_ROLE_ARN${NC}\n"

# Step 2: Create S3 bucket for reports
echo -e "${BLUE}🪣 Step 2: Creating S3 bucket for reports${NC}"

# Create bucket
aws s3 mb s3://$REPORT_BUCKET --region $AWS_REGION

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

echo -e "${GREEN}✅ S3 bucket created: s3://$REPORT_BUCKET${NC}\n"

# Step 3: Create Secrets Manager secret
echo -e "${BLUE}🔑 Step 3: Creating AWS Secrets Manager secret${NC}"

echo -e "${YELLOW}Please provide your API keys (press Enter to skip any):${NC}"

read -p "OpenAI API Key: " -s OPENAI_KEY
echo
read -p "Anthropic API Key: " -s ANTHROPIC_KEY
echo
read -p "Semantic Scholar API Key: " -s S2_KEY
echo
read -p "GitHub Token: " -s GITHUB_TOKEN
echo

# Create secret JSON
SECRET_JSON=$(cat <<EOF
{
    "OPENAI_API_KEY": "$OPENAI_KEY",
    "ANTHROPIC_API_KEY": "$ANTHROPIC_KEY",
    "SEMANTIC_SCHOLAR_API_KEY": "$S2_KEY",
    "GITHUB_TOKEN": "$GITHUB_TOKEN"
}
EOF
)

# Create or update secret
aws secretsmanager create-secret \
    --name $SECRET_NAME \
    --description "API keys for AI Research Weekly pipeline" \
    --secret-string "$SECRET_JSON" \
    --region $AWS_REGION 2>/dev/null || \
aws secretsmanager update-secret \
    --secret-id $SECRET_NAME \
    --secret-string "$SECRET_JSON" \
    --region $AWS_REGION

echo -e "${GREEN}✅ Secrets Manager secret created/updated: $SECRET_NAME${NC}\n"

# Step 4: Set up GitHub repository secrets
echo -e "${BLUE}🐙 Step 4: Setting up GitHub repository secrets${NC}"

if [ "$GH_CLI_AVAILABLE" = true ]; then
    echo -e "${YELLOW}Setting up GitHub secrets automatically...${NC}"
    
    # Check if we're in the right repo
    if ! gh repo view $GITHUB_ORG/$GITHUB_REPO &> /dev/null; then
        echo -e "${RED}❌ Cannot access repository $GITHUB_ORG/$GITHUB_REPO${NC}"
        echo -e "${RED}   Please make sure you're authenticated with GitHub CLI${NC}"
        echo -e "${RED}   Run: gh auth login${NC}"
        exit 1
    fi
    
    # Set secrets using GitHub CLI
    echo "$GITHUB_ROLE_ARN" | gh secret set AWS_ROLE_TO_ASSUME -R $GITHUB_ORG/$GITHUB_REPO
    echo "$REPORT_BUCKET" | gh secret set REPORT_BUCKET -R $GITHUB_ORG/$GITHUB_REPO
    echo "$SECRET_NAME" | gh secret set SECRET_NAME -R $GITHUB_ORG/$GITHUB_REPO
    echo "openai" | gh secret set LLM_BACKEND -R $GITHUB_ORG/$GITHUB_REPO
    echo "gpt-4o-mini" | gh secret set LLM_MODEL -R $GITHUB_ORG/$GITHUB_REPO
    
    # Optional secrets (you can set these later)
    echo "" | gh secret set SES_SENDER -R $GITHUB_ORG/$GITHUB_REPO
    echo "" | gh secret set SUBSCRIBERS -R $GITHUB_ORG/$GITHUB_REPO
    
    echo -e "${GREEN}✅ GitHub secrets set automatically${NC}\n"
else
    echo -e "${YELLOW}⚠️  Please set the following secrets manually in your GitHub repository:${NC}"
    echo -e "${YELLOW}   Go to: https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/secrets/actions${NC}\n"
    
    echo -e "${BLUE}Required secrets:${NC}"
    echo "AWS_ROLE_TO_ASSUME: $GITHUB_ROLE_ARN"
    echo "REPORT_BUCKET: $REPORT_BUCKET"
    echo "SECRET_NAME: $SECRET_NAME"
    echo "LLM_BACKEND: openai"
    echo "LLM_MODEL: gpt-4o-mini"
    echo ""
    echo -e "${BLUE}Optional secrets (for email notifications):${NC}"
    echo "SES_SENDER: your-verified-email@example.com"
    echo "SUBSCRIBERS: email1@example.com,email2@example.com"
    echo ""
fi

# Step 5: Summary and next steps
echo -e "${BLUE}📋 Step 5: Setup Summary${NC}"
echo -e "${GREEN}✅ GitHub OIDC Provider created${NC}"
echo -e "${GREEN}✅ IAM Role for GitHub Actions: $GITHUB_ROLE_ARN${NC}"
echo -e "${GREEN}✅ S3 Bucket for reports: $REPORT_BUCKET${NC}"
echo -e "${GREEN}✅ Secrets Manager secret: $SECRET_NAME${NC}"
echo -e "${GREEN}✅ GitHub repository secrets configured${NC}\n"

echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "1. Push your code to the main branch to trigger the CI/CD pipeline"
echo "2. Monitor the GitHub Actions workflow at: https://github.com/$GITHUB_ORG/$GITHUB_REPO/actions"
echo "3. Check CloudWatch logs for Lambda execution details"
echo "4. Verify reports are being published to S3: https://s3.console.aws.amazon.com/s3/buckets/$REPORT_BUCKET"
echo ""

echo -e "${BLUE}📧 Optional: Set up SES for email notifications${NC}"
echo "1. Verify your sender email in AWS SES"
echo "2. Add SES_SENDER and SUBSCRIBERS to GitHub secrets"
echo "3. Ensure your AWS account is out of SES sandbox if sending to unverified emails"
echo ""

echo -e "${BLUE}🧪 Test the pipeline manually:${NC}"
echo "aws lambda invoke --function-name ai-research-weekly --payload '{}' response.json && cat response.json"
echo ""

echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo -e "${GREEN}Your AI Research Weekly pipeline is now ready for seamless CI/CD!${NC}"