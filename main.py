#!/usr/bin/env python3
import os
import sys
import argparse
import json
from pathlib import Path
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.crawl_local_files import crawl_local_files
from utils.crawl_github_files import crawl_github_files

def main():
    parser = argparse.ArgumentParser(description="Generate a tutorial from a GitHub repository or local directory")

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--repo", help="GitHub repository URL")
    source_group.add_argument("--dir", help="Local directory path")
    
    parser.add_argument("-n", "--name", help="Project name (derived from URL/directory if omitted)")
    parser.add_argument("-t", "--token", help="GitHub token (or set GITHUB_TOKEN environment variable)")
    parser.add_argument("-o", "--output", default="./output", help="Output directory")
    parser.add_argument("-i", "--include", nargs="+", help="Files to include (e.g., '*.py' '*.js')")
    parser.add_argument("-e", "--exclude", nargs="+", help="Files to exclude (e.g., 'tests/*' 'docs/*')")
    parser.add_argument("-s", "--max-size", type=int, default=100000, help="Maximum file size in bytes (default: 100KB)")
    parser.add_argument("--language", default="english", help="Language for the generated tutorial")
    parser.add_argument("--analysis-mode", choices=["fast", "detailed"], default="fast", 
                       help="Analysis mode: 'fast' (5 files max, built-in API) or 'detailed' (requires user API key)")
    parser.add_argument("--user-api-key", help="User's Gemini API key (required for detailed analysis)")

    args = parser.parse_args()

    # Set up shared data store
    shared = {
        "repo_url": args.repo,
        "local_dir": args.dir,
        "project_name": args.name,
        "github_token": args.token or os.environ.get("GITHUB_TOKEN"),
        "output_dir": args.output,
        "include_patterns": set(args.include) if args.include else None,
        "exclude_patterns": set(args.exclude) if args.exclude else None,
        "max_file_size": args.max_size,
        "language": args.language,
        "analysis_mode": args.analysis_mode,
        "user_api_key": args.user_api_key
    }
    
    # Validate analysis mode requirements
    if args.analysis_mode == "detailed" and not args.user_api_key:
        print("Error: --user-api-key is required for detailed analysis mode")
        print("Please provide your Gemini API key for comprehensive analysis")
        sys.exit(1)
    
    # Import here to avoid circular imports
    from flow import create_tutorial_flow
    
    # Create and run the tutorial flow
    tutorial_flow = create_tutorial_flow()
    tutorial_flow.run(shared)
    
    # Get the output directory from shared store
    tutorial_dir = shared.get("tutorial_dir", "")
    if tutorial_dir and os.path.exists(tutorial_dir):
        print(f"\nTutorial generated successfully at: {tutorial_dir}")
        
        print("\nValidating and fixing Mermaid diagrams...")
        try:
            validation_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_mermaid.py")
            result = subprocess.run(
                [sys.executable, validation_script, tutorial_dir, '--fix', '--recursive'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.stdout:
                print("Validation script output:")
                print(result.stdout)
            if result.stderr:
                print("Validation script errors/warnings:")
                print(result.stderr)
                
            if result.returncode == 0:
                print("Mermaid validation and fixing completed successfully.")
            else:
                print(f"Mermaid validation script finished with exit code {result.returncode}.")
        except FileNotFoundError:
             print(f"Error: validate_mermaid.py script not found. Skipping Mermaid validation.")
        except Exception as e:
            print(f"An error occurred during Mermaid validation: {e}")
            
    else:
        print("\nFailed to generate tutorial.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
