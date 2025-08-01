"""Local development runner for AI Weekly pipeline."""

import os
import sys
from pathlib import Path

# Add the parent directory to path so we can import ai_weekly modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_weekly.lambda_handler import run_pipeline

if __name__ == "__main__":
    # Load environment variables from .env file if available
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("python-dotenv not installed, using system environment variables")

    # Run the pipeline
    print("Starting AI Weekly pipeline...")
    result = run_pipeline()

    # Exit with appropriate code
    if result.get("statusCode") == 200:
        print("Pipeline completed successfully!")
        sys.exit(0)
    else:
        print("Pipeline failed!")
        sys.exit(1)
