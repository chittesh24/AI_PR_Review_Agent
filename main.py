# main.py - Orchestrator for AI PR Review Agent (Llama via Ollama)
import os
from ai_pr_reviewer.github_api import get_installation_client, fetch_pr_data
from ai_pr_reviewer.analyzers import run_static_analysis
from ai_pr_reviewer.ai_agent import generate_review
from ai_pr_reviewer.reporter import post_review_comments

def main():
    # Load configuration from environment
    repo_full = os.getenv("GITHUB_REPOSITORY")
    pr_number = int(os.getenv("PR_NUMBER", "0"))
    if not repo_full or pr_number == 0:
        print("Missing GITHUB_REPOSITORY or PR_NUMBER environment variables. Exiting.")
        return

    print(f"Starting AI PR Review for {repo_full}#{pr_number}")

    # Authenticate as GitHub App installation and create a PyGithub client
    gh = get_installation_client()

    owner, repo_name = repo_full.split('/')
    print("Fetching PR files...")
    files = fetch_pr_data(gh, owner, repo_name, pr_number)

    print(f"Found {len(files)} changed files. Running analyzers...")
    analysis = run_static_analysis(files)

    print("Sending diff + analysis to Llama (Ollama)...")
    diff_text = "\n\n".join([f'File: {f.filename}\n' + (f.patch or '') for f in files])[:30000]
    ai_result = generate_review(diff_text, analysis)

    print("AI result summary:\n", ai_result.get('summary', '')[:2000])
    findings = ai_result.get('findings', [])

    print("Posting review comments to GitHub...")
    post_review_comments(gh, owner, repo_name, pr_number, findings, ai_result.get('summary', ''))

    print("Completed AI PR Review.")


if __name__ == '__main__':
    main()
