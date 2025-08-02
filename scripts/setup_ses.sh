#!/bin/bash

# Script to set up Amazon SES for AI Research Weekly email notifications

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "AI Research Weekly - SES Setup Script"
echo "======================================"
echo ""

# Configuration
REGION="us-east-1"
SENDER_EMAIL=""
RECIPIENT_EMAILS=""

# Get sender email
echo -e "${YELLOW}Enter the sender email address (must be verified in SES):${NC}"
read -p "Sender Email: " SENDER_EMAIL

if [ -z "$SENDER_EMAIL" ]; then
    echo -e "${RED}Error: Sender email is required${NC}"
    exit 1
fi

# Validate email format
if ! [[ "$SENDER_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    echo -e "${RED}Error: Invalid email format${NC}"
    exit 1
fi

# Get recipient emails
echo ""
echo -e "${YELLOW}Enter recipient email addresses (comma-separated, press Enter to skip):${NC}"
read -p "Recipients: " RECIPIENT_EMAILS

echo ""
echo "======================================"
echo "Step 1: Verifying Sender Email"
echo "======================================"

# Check if sender email is already verified
VERIFIED=$(aws ses list-verified-email-addresses --region $REGION --query "VerifiedEmailAddresses[?@=='$SENDER_EMAIL']" --output text 2>/dev/null || echo "")

if [ -n "$VERIFIED" ]; then
    echo -e "${GREEN}✓ Sender email $SENDER_EMAIL is already verified${NC}"
else
    echo "Sending verification email to $SENDER_EMAIL..."
    aws ses verify-email-identity --email-address "$SENDER_EMAIL" --region $REGION
    echo -e "${YELLOW}⚠ Verification email sent to $SENDER_EMAIL${NC}"
    echo "Please check your inbox and click the verification link before proceeding."
    echo ""
    read -p "Press Enter after you've verified the email address..."
    
    # Check again
    VERIFIED=$(aws ses list-verified-email-addresses --region $REGION --query "VerifiedEmailAddresses[?@=='$SENDER_EMAIL']" --output text 2>/dev/null || echo "")
    if [ -n "$VERIFIED" ]; then
        echo -e "${GREEN}✓ Email verified successfully${NC}"
    else
        echo -e "${RED}✗ Email not verified. Please verify and run this script again.${NC}"
        exit 1
    fi
fi

echo ""
echo "======================================"
echo "Step 2: Checking SES Sending Quota"
echo "======================================"

# Get sending quota
QUOTA=$(aws ses describe-configuration-set --region $REGION 2>/dev/null || aws ses get-send-quota --region $REGION)
echo "Current SES sending quota:"
echo "$QUOTA" | jq '.'

echo ""
echo "======================================"
echo "Step 3: Testing Email Sending"
echo "======================================"

# Create test email
TEST_SUBJECT="AI Research Weekly - SES Test Email"
TEST_BODY="This is a test email from AI Research Weekly to verify SES configuration.

If you received this email, your SES setup is working correctly!

This email was sent from the automated AI Research Weekly pipeline."

echo "Sending test email from $SENDER_EMAIL to $SENDER_EMAIL..."

aws ses send-email \
    --from "$SENDER_EMAIL" \
    --to "$SENDER_EMAIL" \
    --subject "$TEST_SUBJECT" \
    --text "$TEST_BODY" \
    --region $REGION

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Test email sent successfully!${NC}"
    echo "Please check your inbox for the test email."
else
    echo -e "${RED}✗ Failed to send test email${NC}"
    exit 1
fi

echo ""
echo "======================================"
echo "Step 4: Updating GitHub Secrets"
echo "======================================"

echo "To complete the setup, add these secrets to your GitHub repository:"
echo ""
echo -e "${YELLOW}Required GitHub Secrets:${NC}"
echo "  SES_SENDER: $SENDER_EMAIL"
if [ -n "$RECIPIENT_EMAILS" ]; then
    echo "  SUBSCRIBERS: $RECIPIENT_EMAILS"
fi

echo ""
echo "You can add these secrets manually at:"
echo "https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/settings/secrets/actions"

echo ""
echo -e "${YELLOW}Or run these commands to add them via GitHub CLI:${NC}"
echo ""
echo "gh secret set SES_SENDER --body \"$SENDER_EMAIL\""
if [ -n "$RECIPIENT_EMAILS" ]; then
    echo "gh secret set SUBSCRIBERS --body \"$RECIPIENT_EMAILS\""
fi

echo ""
read -p "Would you like to add these secrets now? (y/n): " ADD_SECRETS

if [ "$ADD_SECRETS" = "y" ] || [ "$ADD_SECRETS" = "Y" ]; then
    echo "$SENDER_EMAIL" | gh secret set SES_SENDER
    echo -e "${GREEN}✓ Added SES_SENDER secret${NC}"
    
    if [ -n "$RECIPIENT_EMAILS" ]; then
        echo "$RECIPIENT_EMAILS" | gh secret set SUBSCRIBERS
        echo -e "${GREEN}✓ Added SUBSCRIBERS secret${NC}"
    fi
fi

echo ""
echo "======================================"
echo "Step 5: Production Access (Optional)"
echo "======================================"

echo "Your AWS SES account may be in the sandbox environment, which limits:"
echo "  - Sending only to verified email addresses"
echo "  - Maximum 200 emails per day"
echo "  - Maximum 1 email per second"
echo ""
echo "For production use, you can request to move out of the sandbox:"
echo "https://console.aws.amazon.com/ses/home?region=$REGION#/account"
echo ""
echo "Click 'Request production access' and fill out the form."

echo ""
echo "======================================"
echo -e "${GREEN}✓ SES Setup Complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Ensure GitHub secrets are configured (SES_SENDER and optionally SUBSCRIBERS)"
echo "2. Redeploy the Lambda function to pick up the new configuration"
echo "3. The pipeline will now send email reports every Sunday at 10 PM UTC"
echo ""
echo "To trigger a manual run with email:"
echo "  gh workflow run ci-cd.yml"
echo ""
echo "To monitor emails:"
echo "  https://console.aws.amazon.com/ses/home?region=$REGION#/metrics"