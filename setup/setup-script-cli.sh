#!/bin/bash

# AI Research Weekly - GitHub CI/CD Setup Script (CLI Version)
# This script uses AWS CLI directly instead of CloudFormation for OIDC setup

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
AWS_REGION="eu-west-2"      # Your preferred region for the main stack
REPORT_BUCKET="ai-research-weekly-reports-$(date +%s)"  # Unique bucket name
SECRET_NAME="ai-weekly/api-keys"
ROLE_NAME="ai-weekly-github-actions-role"

echo -e "${BLUE}🚀 Setting up AI Research Weekly CI/CD Pipeline (CLI Version)${NC}"
echo -e "${BLUE}================================================================${NC}\n"

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

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check GitHub CLI (optional but recommended)
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI not found. You'll need to set secrets manually.${NC}"
    GH_CLI_AVAILABLE=false
else
    GH_CLI_AVAILABLE=true
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"
echo -e "${GREEN}   AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}   Region: $AWS_REGION${NC}\n"

# Step 1: Create GitHub OIDC Provider
echo -e "${BLUE}🔐 Step 1: Creating GitHub OIDC Identity Provider${NC}"

# Check if OIDC provider already exists
OIDC_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_ARN" &> /dev/null; then
    echo -e "${GREEN}✅ GitHub OIDC provider already exists${NC}"
else
    echo -e "${YELLOW}Creating GitHub OIDC provider...${NC}"
    
    # Create OIDC provider - this is global and works from any region
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --client-id-list sts.amazonaws.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 1c58a3a8518e8759bf075b76b750d4f2df264fcd
    
    echo -e "${GREEN}✅ GitHub OIDC provider created${NC}"
fi

echo -e "${GREEN}   OIDC Provider ARN: $OIDC_ARN${NC}\n"

# Step 2: Create IAM Role for GitHub Actions
echo -e "${BLUE}🔑 Step 2: Creating IAM Role for GitHub Actions${NC}"

# Create trust policy
cat > trust-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "$OIDC_ARN"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": [
                        "repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/main",
                        "repo:$GITHUB_ORG/$GITHUB_REPO:pull_request"
                    ]
                }
            }
        }
    ]
}
EOF

# Create permissions policy
cat > permissions-policy.json <<EOF
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
EOF

# Check if role already exists
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    echo -e "${YELLOW}Role already exists, updating policies...${NC}"
    
    # Update trust policy
    aws iam update-assume-role-policy \
        --role-name $ROLE_NAME \
        --policy-document file://trust-policy.json
    
    # Update permissions policy
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name SAMDeploymentPolicy \
        --policy-document file://permissions-policy.json
else
    echo -e "${YELLOW}Creating new IAM role...${NC}"
    
    # Create role
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json \
        --description "GitHub Actions role for AI Research Weekly"
    
    # Attach permissions policy
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name SAMDeploymentPolicy \
        --policy-document file://permissions-policy.json
fi

# Get role ARN
GITHUB_ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

echo -e "${GREEN}✅ IAM role configured${NC}"
echo -e "${GREEN}   Role ARN: $GITHUB_ROLE_ARN${NC}\n"

# Clean up temporary files
rm -f trust-policy.json permissions-policy.json

# Step 3: Create S3 bucket for reports
echo -e "${BLUE}🪣 Step 3: Creating S3 bucket for reports${NC}"

# Create bucket with region-specific configuration
if [ "$AWS_REGION" = "us-east-1" ]; then
    aws s3 mb s3://$REPORT_BUCKET
else
    aws s3 mb s3://$REPORT_BUCKET --region $AWS_REGION
fi

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

# Step 4: Create Secrets Manager secret
echo -e "${BLUE}🔑 Step 4: Creating AWS Secrets Manager secret${NC}"

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

# Step 5: Set up GitHub repository secrets
echo -e "${BLUE}🐙 Step 5: Setting up GitHub repository secrets${NC}"

if [ "$GH_CLI_AVAILABLE" = true ]; then
    echo -e "${YELLOW}Setting up GitHub secrets automatically...${NC}"
    
    # Check if we're in the right repo
    if ! gh repo view $GITHUB_ORG/$GITHUB_REPO &> /dev/null; then
        echo -e "${RED}❌ Cannot access repository $GITHUB_ORG/$GITHUB_REPO${NC}"
        echo -e "${RED}   Please make sure you're authenticated with GitHub CLI${NC}"
        echo -e "${RED}   Run: gh auth login${NC}"
        echo -e "${YELLOW}   Or set secrets manually using the information below${NC}\n"
        GH_CLI_AVAILABLE=false
    else
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
    fi
fi

if [ "$GH_CLI_AVAILABLE" = false ]; then
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

# Step 6: Summary and next steps
echo -e "${BLUE}📋 Step 6: Setup Summary${NC}"
echo -e "${GREEN}✅ GitHub OIDC Provider created${NC}"
echo -e "${GREEN}✅ IAM Role for GitHub Actions: $GITHUB_ROLE_ARN${NC}"
echo -e "${GREEN}✅ S3 Bucket for reports: $REPORT_BUCKET${NC}"
echo -e "${GREEN}✅ Secrets Manager secret: $SECRET_NAME${NC}"
echo -e "${GREEN}✅ GitHub repository secrets configured${NC}\n"

echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "1. Update your SAM template to use the correct region:"
echo "   Edit template.yaml and update any region-specific resources"
echo ""
echo "2. Deploy your application:"
echo "   cd .."
echo "   sam build --use-container"
echo "   sam deploy --guided --region $AWS_REGION"
echo ""
echo "3. Push your code to trigger the CI/CD pipeline:"
echo "   git add ."
echo "   git commit -m 'Add CI/CD setup'"
echo "   git push origin main"
echo ""
echo "4. Monitor the GitHub Actions workflow at:"
echo "   https://github.com/$GITHUB_ORG/$GITHUB_REPO/actions"
echo ""

echo -e "${BLUE}📧 Optional: Set up SES for email notifications${NC}"
echo "1. Verify your sender email in AWS SES:"
echo "   aws ses verify-email-identity --email-address your-email@example.com --region $AWS_REGION"
echo "2. Add SES_SENDER and SUBSCRIBERS to GitHub secrets"
echo "3. Ensure your AWS account is out of SES sandbox if sending to unverified emails"
echo ""

echo -e "${BLUE}🧪 Test the pipeline manually after deployment:${NC}"
echo "aws lambda invoke --function-name ai-research-weekly --payload '{}' --region $AWS_REGION response.json && cat response.json"
echo ""

echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo -e "${GREEN}Your AI Research Weekly pipeline is now ready for seamless CI/CD!${NC}"