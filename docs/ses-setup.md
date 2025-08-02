# Amazon SES Setup for AI Research Weekly

This guide walks you through setting up Amazon Simple Email Service (SES) to enable email notifications for the AI Research Weekly pipeline.

## Prerequisites

- AWS CLI configured with appropriate credentials
- GitHub CLI (`gh`) installed for managing secrets
- Access to the email addresses you want to verify

## Quick Setup

Run the automated setup script:

```bash
./scripts/setup_ses.sh
```

This script will:
1. Verify your sender email address
2. Test email sending capability
3. Help you configure GitHub secrets
4. Provide guidance on production access

## Manual Setup Steps

### 1. Verify Email Addresses

Verify the sender email address in SES:

```bash
# Verify sender email
aws ses verify-email-identity \
  --email-address your-email@example.com \
  --region us-east-1

# List verified emails
aws ses list-verified-email-addresses --region us-east-1
```

Check your inbox and click the verification link from AWS.

### 2. Test Email Sending

Send a test email to verify configuration:

```bash
aws ses send-email \
  --from your-email@example.com \
  --to your-email@example.com \
  --subject "AI Research Weekly Test" \
  --text "Test email from AI Research Weekly" \
  --region us-east-1
```

### 3. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

```bash
# Set sender email
gh secret set SES_SENDER --body "your-email@example.com"

# Set subscriber list (optional, comma-separated)
gh secret set SUBSCRIBERS --body "subscriber1@example.com,subscriber2@example.com"
```

Or add them manually at:
`https://github.com/YOUR_USERNAME/ai-research/settings/secrets/actions`

### 4. Redeploy Lambda Function

After adding secrets, redeploy to apply the configuration:

```bash
# Trigger deployment
git commit --allow-empty -m "chore: Redeploy with SES configuration"
git push origin main
```

## Configuration Options

### Environment Variables

The Lambda function uses these environment variables for email:

- `SES_SENDER`: Verified sender email address (required for email)
- `SUBSCRIBERS`: Comma-separated list of recipient emails (optional)

### SES Regions

The pipeline uses `us-east-1` by default. To use a different region:
1. Update the region in `template.yaml`
2. Verify emails in that region
3. Update the GitHub Actions workflow

## Sandbox vs Production

### Sandbox Mode (Default)
- **Limits**: 200 emails/day, 1 email/second
- **Recipients**: Only verified email addresses
- **Use case**: Testing and development

### Production Mode
- **Limits**: Higher quotas based on reputation
- **Recipients**: Any valid email address
- **Use case**: Production deployments

To request production access:
1. Go to [SES Console](https://console.aws.amazon.com/ses/home?region=us-east-1#/account)
2. Click "Request production access"
3. Fill out the form with:
   - Use case: Transactional emails for AI research digest subscribers
   - Expected volume: Weekly emails to subscribers
   - Bounce/complaint handling: Automated via SES

## Email Features

### Email Content
The pipeline sends:
- **Subject**: "AI Research Weekly - YYYY-MM-DD"
- **Body**: Markdown report converted to HTML and plain text
- **Attachments**: None (links to S3 reports included)

### Scheduling
Emails are sent:
- Every Sunday at 10 PM UTC (automated)
- On manual pipeline runs (if configured)

### Monitoring

View email metrics in the [SES Console](https://console.aws.amazon.com/ses/home?region=us-east-1#/metrics):
- Send rate
- Bounce rate
- Complaint rate
- Reputation metrics

## Troubleshooting

### Email Not Sending

1. **Check verification status**:
   ```bash
   aws ses list-verified-email-addresses --region us-east-1
   ```

2. **Check Lambda logs**:
   ```bash
   aws logs tail /aws/lambda/ai-research-weekly --follow
   ```

3. **Verify secrets are set**:
   ```bash
   gh secret list
   ```

### Verification Email Not Received

1. Check spam/junk folder
2. Ensure email address is correct
3. Resend verification:
   ```bash
   aws ses verify-email-identity --email-address your-email@example.com
   ```

### Bounce/Complaint Handling

Consider setting up:
1. SES suppression list (automatic)
2. SNS notifications for bounces/complaints
3. CloudWatch alarms for high bounce rates

## Best Practices

1. **Start in sandbox**: Test thoroughly before requesting production
2. **Monitor metrics**: Watch bounce/complaint rates
3. **Use suppression list**: Automatically handle bounces
4. **Implement unsubscribe**: Add unsubscribe links in emails
5. **Warm up sending**: Gradually increase volume in production
6. **Keep lists clean**: Remove invalid/bounced addresses

## Verification Script

Check your SES configuration:

```bash
python scripts/verify_ses.py
```

This shows:
- SES status
- Verified emails
- Sending quotas
- Sandbox/production mode

## Cost

SES pricing (us-east-1):
- First 62,000 emails/month: Free (from EC2/Lambda)
- Additional emails: $0.10 per 1,000 emails
- Data transfer: $0.12 per GB for attachments

For weekly digests to 100 subscribers:
- ~400 emails/month = Free tier
- No attachments = No data transfer costs

## Next Steps

After setup:
1. ✅ Run `./scripts/setup_ses.sh` to verify emails
2. ✅ Add GitHub secrets (SES_SENDER, SUBSCRIBERS)
3. ✅ Redeploy Lambda function
4. ⏳ Wait for Sunday 10 PM UTC for automated run
5. 📧 Or trigger manual run: `gh workflow run ci-cd.yml`

## Support

For issues:
- Check CloudWatch logs: `/aws/lambda/ai-research-weekly`
- Review SES metrics in AWS Console
- Open issue on GitHub repository