import os
from ai_pr_reviewer.github_api import fetch_pr_data, fetch_pr_meta
from ai_pr_reviewer.analyzers import run_static_analysis
from ai_pr_reviewer.ai_agent import generate_review
from ai_pr_reviewer.reporter import create_check_with_annotations, post_review_comment

def main():
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repo or not token:
        print('GITHUB_REPOSITORY or GITHUB_TOKEN not set. Exiting.')
        return
    owner, repo_name = repo.split('/')
    event_pr = os.getenv('PR_NUMBER')
    # Attempt to read PR number from GitHub event path if available
    import json, os
    event_path = os.getenv('GITHUB_EVENT_PATH')
    pr_number = None
    if event_path and os.path.exists(event_path):
        with open(event_path, 'r') as f:
            ev = json.load(f)
            pr_number = ev.get('pull_request', {}).get('number')
    if not pr_number and event_pr:
        pr_number = int(event_pr)
    if not pr_number:
        print('PR number not found. Exiting.')
        return
    print(f'Running AI PR Review for {owner}/{repo_name}#{pr_number}')

    diff, head_sha = fetch_pr_data(owner, repo_name, pr_number, token)
    analysis = run_static_analysis()
    ai_review = generate_review(diff, analysis)
    summary = ai_review.get('summary', '') if isinstance(ai_review, dict) else str(ai_review)
    findings = ai_review.get('findings', []) if isinstance(ai_review, dict) else []

    # Create check run with annotations
    create_check_with_annotations(owner, repo_name, head_sha, 'AI PR Review', summary, findings, token)
    # Post a compact PR review comment
    post_review_comment(owner, repo_name, pr_number, summary, token)
    print('Completed AI PR Review.')

if __name__ == '__main__':
    main()
