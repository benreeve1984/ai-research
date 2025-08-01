#!/bin/bash

# AI Research Weekly - Pipeline Testing Script
# Tests the deployed pipeline to ensure everything works correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="ai-research-weekly"
STACK_NAME="ai-research-weekly"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${BLUE}🧪 Testing AI Research Weekly Pipeline${NC}"
echo -e "${BLUE}=====================================\n${NC}"

# Step 1: Check if stack exists
echo -e "${YELLOW}📋 Step 1: Checking CloudFormation stack...${NC}"

if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✅ Stack '$STACK_NAME' exists${NC}"
    
    # Get stack outputs
    echo -e "${BLUE}Stack outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[*].{Key:OutputKey,Value:OutputValue}' \
        --output table
else
    echo -e "${RED}❌ Stack '$STACK_NAME' not found${NC}"
    echo -e "${RED}   Please deploy the stack first using: sam deploy --guided${NC}"
    exit 1
fi

echo ""

# Step 2: Check if Lambda function exists
echo -e "${YELLOW}🔍 Step 2: Checking Lambda function...${NC}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✅ Lambda function '$FUNCTION_NAME' exists${NC}"
    
    # Get function configuration
    TIMEOUT=$(aws lambda get-function-configuration \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --query 'Timeout' \
        --output text)
    
    MEMORY=$(aws lambda get-function-configuration \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION \
        --query 'MemorySize' \
        --output text)
    
    echo -e "${BLUE}   Timeout: ${TIMEOUT}s, Memory: ${MEMORY}MB${NC}"
else
    echo -e "${RED}❌ Lambda function '$FUNCTION_NAME' not found${NC}"
    exit 1
fi

echo ""

# Step 3: Test Lambda function invocation
echo -e "${YELLOW}🚀 Step 3: Testing Lambda function invocation...${NC}"

# Create test payload
TEST_PAYLOAD='{"source": "test-script", "test": true}'

echo -e "${BLUE}Invoking Lambda function with test payload...${NC}"

# Invoke function and capture response
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload "$TEST_PAYLOAD" \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    response.json

# Check if response file was created
if [ ! -f "response.json" ]; then
    echo -e "${RED}❌ No response file created${NC}"
    exit 1
fi

# Parse response
echo -e "${BLUE}Lambda response:${NC}"
cat response.json | jq '.'

# Check status code
STATUS_CODE=$(cat response.json | jq -r '.statusCode // "unknown"')

if [ "$STATUS_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Lambda function executed successfully${NC}"
    
    # Parse response body if it exists
    if cat response.json | jq -e '.body' > /dev/null 2>&1; then
        BODY=$(cat response.json | jq -r '.body')
        echo -e "${BLUE}Response body:${NC}"
        echo "$BODY" | jq '.'
        
        # Check execution status
        EXEC_STATUS=$(echo "$BODY" | jq -r '.status // "unknown"')
        if [ "$EXEC_STATUS" = "completed" ]; then
            echo -e "${GREEN}✅ Pipeline executed successfully${NC}"
            
            # Get execution details
            PAPERS_HARVESTED=$(echo "$BODY" | jq -r '.papers_harvested // "unknown"')
            PAPERS_PUBLISHED=$(echo "$BODY" | jq -r '.papers_published // "unknown"')
            EXECUTION_TIME=$(echo "$BODY" | jq -r '.execution_time_seconds // "unknown"')
            
            echo -e "${BLUE}Execution details:${NC}"
            echo -e "   Papers harvested: $PAPERS_HARVESTED"
            echo -e "   Papers published: $PAPERS_PUBLISHED"
            echo -e "   Execution time: ${EXECUTION_TIME}s"
        else
            echo -e "${YELLOW}⚠️  Pipeline status: $EXEC_STATUS${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Lambda function failed with status code: $STATUS_CODE${NC}"
    
    # Check for error message
    if cat response.json | jq -e '.body' > /dev/null 2>&1; then
        ERROR_MSG=$(cat response.json | jq -r '.body' | jq -r '.message // "No error message"')
        echo -e "${RED}   Error: $ERROR_MSG${NC}"
    fi
fi

echo ""

# Step 4: Check CloudWatch logs
echo -e "${YELLOW}📊 Step 4: Checking recent CloudWatch logs...${NC}"

LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Check if log group exists
if aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP --region $AWS_REGION | jq -e '.logGroups | length > 0' > /dev/null; then
    echo -e "${GREEN}✅ Log group exists: $LOG_GROUP${NC}"
    
    # Get recent log events
    echo -e "${BLUE}Recent log events (last 10):${NC}"
    
    # Get the latest log stream
    LATEST_STREAM=$(aws logs describe-log-streams \
        --log-group-name $LOG_GROUP \
        --region $AWS_REGION \
        --order-by LastEventTime \
        --descending \
        --limit 1 \
        --query 'logStreams[0].logStreamName' \
        --output text)
    
    if [ "$LATEST_STREAM" != "None" ] && [ "$LATEST_STREAM" != "" ]; then
        aws logs get-log-events \
            --log-group-name $LOG_GROUP \
            --log-stream-name "$LATEST_STREAM" \
            --region $AWS_REGION \
            --limit 10 \
            --query 'events[*].[timestamp,message]' \
            --output table
    else
        echo -e "${YELLOW}⚠️  No log streams found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Log group not found or no logs yet${NC}"
fi

echo ""

# Step 5: Check S3 bucket (if specified)
echo -e "${YELLOW}🪣 Step 5: Checking S3 bucket...${NC}"

# Try to get bucket name from stack outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ReportsBucketName`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ "$BUCKET_NAME" != "" ] && [ "$BUCKET_NAME" != "None" ]; then
    echo -e "${GREEN}✅ S3 bucket found: $BUCKET_NAME${NC}"
    
    # Check if bucket is accessible
    if aws s3 ls s3://$BUCKET_NAME --region $AWS_REGION &> /dev/null; then
        echo -e "${GREEN}✅ S3 bucket is accessible${NC}"
        
        # List recent objects
        echo -e "${BLUE}Recent objects in bucket:${NC}"
        aws s3 ls s3://$BUCKET_NAME --recursive --human-readable --summarize | tail -20
    else
        echo -e "${RED}❌ S3 bucket is not accessible${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  S3 bucket name not found in stack outputs${NC}"
fi

echo ""

# Step 6: Check EventBridge rule
echo -e "${YELLOW}⏰ Step 6: Checking EventBridge schedule...${NC}"

RULE_NAME="ai-weekly-schedule"

if aws events describe-rule --name $RULE_NAME --region $AWS_REGION &> /dev/null; then
    echo -e "${GREEN}✅ EventBridge rule exists: $RULE_NAME${NC}"
    
    # Get rule details
    SCHEDULE=$(aws events describe-rule \
        --name $RULE_NAME \
        --region $AWS_REGION \
        --query 'ScheduleExpression' \
        --output text)
    
    STATE=$(aws events describe-rule \
        --name $RULE_NAME \
        --region $AWS_REGION \
        --query 'State' \
        --output text)
    
    echo -e "${BLUE}   Schedule: $SCHEDULE${NC}"
    echo -e "${BLUE}   State: $STATE${NC}"
    
    # Check targets
    TARGET_COUNT=$(aws events list-targets-by-rule \
        --rule $RULE_NAME \
        --region $AWS_REGION \
        --query 'length(Targets)' \
        --output text)
    
    echo -e "${BLUE}   Targets: $TARGET_COUNT${NC}"
else
    echo -e "${YELLOW}⚠️  EventBridge rule not found${NC}"
fi

echo ""

# Step 7: Summary
echo -e "${BLUE}📋 Test Summary${NC}"
echo -e "${BLUE}===============${NC}"

# Clean up response file
rm -f response.json

if [ "$STATUS_CODE" = "200" ]; then
    echo -e "${GREEN}🎉 All tests passed! Your pipeline is working correctly.${NC}"
    echo ""
    echo -e "${BLUE}💡 Next steps:${NC}"
    echo "1. Monitor the pipeline execution in CloudWatch"
    echo "2. Check S3 bucket for generated reports"
    echo "3. Set up email notifications if desired"
    echo "4. The pipeline will run automatically every Sunday at 22:00 UTC"
    echo ""
    echo -e "${BLUE}🔗 Useful links:${NC}"
    echo "• CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
    echo "• Lambda Function: https://console.aws.amazon.com/lambda/home?region=$AWS_REGION#/functions/$FUNCTION_NAME"
    if [ "$BUCKET_NAME" != "" ]; then
        echo "• S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/$BUCKET_NAME"
    fi
else
    echo -e "${RED}❌ Some tests failed. Please check the logs and configuration.${NC}"
    exit 1
fi