#!/usr/bin/env python3
"""Verify SES configuration for AI Research Weekly."""

import boto3
import json
import sys
from typing import Dict, List, Optional


def check_ses_configuration(region: str = "us-east-1") -> Dict:
    """Check SES configuration and return status."""
    ses_client = boto3.client("ses", region_name=region)
    status = {
        "enabled": False,
        "verified_emails": [],
        "sending_quota": {},
        "sandbox_mode": True,
        "configuration_sets": [],
        "suppression_list": False,
    }

    try:
        # Check if SES is enabled
        account_status = ses_client.get_account_sending_enabled()
        status["enabled"] = account_status.get("Enabled", False)

        # Get verified email addresses
        verified = ses_client.list_verified_email_addresses()
        status["verified_emails"] = verified.get("VerifiedEmailAddresses", [])

        # Get sending quota
        quota = ses_client.get_send_quota()
        status["sending_quota"] = {
            "max_24_hour_send": quota.get("Max24HourSend", 0),
            "max_send_rate": quota.get("MaxSendRate", 0),
            "sent_last_24_hours": quota.get("SentLast24Hours", 0),
        }

        # Check if in sandbox (sandbox has 200 email limit)
        status["sandbox_mode"] = quota.get("Max24HourSend", 0) <= 200

        # List configuration sets
        config_sets = ses_client.list_configuration_sets()
        status["configuration_sets"] = [
            cs["Name"] for cs in config_sets.get("ConfigurationSets", [])
        ]

        # Check suppression list configuration
        try:
            suppression = ses_client.get_account_suppression_list_status()
            status["suppression_list"] = suppression.get("SuppressionListEnabled", False)
        except:
            pass

    except Exception as e:
        print(f"Error checking SES configuration: {e}", file=sys.stderr)
        return status

    return status


def verify_email_address(email: str, region: str = "us-east-1") -> bool:
    """Send verification email for an address."""
    ses_client = boto3.client("ses", region_name=region)
    
    try:
        ses_client.verify_email_identity(EmailAddress=email)
        return True
    except Exception as e:
        print(f"Error verifying email {email}: {e}", file=sys.stderr)
        return False


def send_test_email(
    sender: str, 
    recipient: str, 
    region: str = "us-east-1"
) -> bool:
    """Send a test email."""
    ses_client = boto3.client("ses", region_name=region)
    
    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": "AI Research Weekly - SES Test"},
                "Body": {
                    "Text": {
                        "Data": "This is a test email from AI Research Weekly.\n\n"
                        "Your SES configuration is working correctly!"
                    }
                },
            },
        )
        print(f"Test email sent! Message ID: {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Error sending test email: {e}", file=sys.stderr)
        return False


def main():
    """Main verification function."""
    print("=" * 50)
    print("AI Research Weekly - SES Configuration Verifier")
    print("=" * 50)
    print()

    # Check SES configuration
    print("Checking SES configuration...")
    config = check_ses_configuration()
    
    print(f"\n✓ SES Enabled: {config['enabled']}")
    print(f"✓ Sandbox Mode: {'Yes (Limited to 200 emails/day)' if config['sandbox_mode'] else 'No (Production)'}")
    
    print(f"\nSending Quota:")
    print(f"  - Max 24-hour send: {config['sending_quota']['max_24_hour_send']}")
    print(f"  - Max send rate: {config['sending_quota']['max_send_rate']}/second")
    print(f"  - Sent last 24 hours: {config['sending_quota']['sent_last_24_hours']}")
    
    if config["verified_emails"]:
        print(f"\nVerified Email Addresses:")
        for email in config["verified_emails"]:
            print(f"  ✓ {email}")
    else:
        print("\n⚠ No verified email addresses found!")
        print("You need to verify at least one email address to send emails.")
        
    print("\n" + "=" * 50)
    
    # Recommendations
    print("\nRecommendations:")
    
    if not config["verified_emails"]:
        print("1. Run ./scripts/setup_ses.sh to verify email addresses")
    
    if config["sandbox_mode"]:
        print("2. Request production access to remove sandbox limitations:")
        print("   https://console.aws.amazon.com/ses/home?region=us-east-1#/account")
    
    if not config["suppression_list"]:
        print("3. Consider enabling suppression list for bounce/complaint handling")
    
    print("\nTo complete SES setup for the pipeline:")
    print("  1. Run: ./scripts/setup_ses.sh")
    print("  2. Add GitHub secrets: SES_SENDER and SUBSCRIBERS")
    print("  3. Redeploy the Lambda function")
    

if __name__ == "__main__":
    main()