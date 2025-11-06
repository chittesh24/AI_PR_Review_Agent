"""
AI PR Review Agent (GPT-5 Mini)
--------------------------------
Automatically reviews GitHub pull requests using OpenAI GPT-5 Mini.

Environment Variables:
- GITHUB_TOKEN       : Provided automatically by GitHub Actions
- OPENAI_API_KEY     : Your OpenAI API key (from repository secrets)
- GITHUB_REPOSITORY  : e.g. chittesh24/AI_PR_Review_Agent
- PR_NUMBER          : Set automatically by workflow

Author: chittesh24
"""

import os
import re
import json
from github import Github
from openai import OpenAI

# --- Environment Setup ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("PR_NUMBER")

if not all([GITHUB_TOKEN, OPENAI_API_KEY, REPO_NAME, PR_NUMBER]):
    raise EnvironmentError("Missing one or more required environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(REPO_NAME)
pr = repo.get_pull(int(PR_NUMBER))

# --- Fetch PR Data ---
def fetch_pr_diff(pr):
    files = pr.get_files()
    diffs = []
    for f in files:
        if not f.patch:
            continue
        diffs.append(f"File: {f.filename}\n{f.patch}")
    return "\n\n".join(diffs)

# --- Generate AI Review ---
def generate_review(diff_text):
    prompt = f"""
You are an expert software engineer reviewing a GitHub Pull Request.

Review the following code changes and provide:
1. A summary comment of overall quality.
2. Line-by-line feedback (FILE:LINE - Comment).

Focus on:
- Code correctness and bugs
- Security issues
- Readability and maintainability
- Testing or missing coverage
- Any risky changes

Code diff:
{diff_text[:6000]}  # limit for token safety
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are a senior developer performing PR reviews."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    review_text = response.choices[0].message.content
    comments = []
    for line in review_text.splitlines():
        match = re.match(r"^\s*([^:]+):(\d+)\s*-\s*(.+)", line)
        if match:
            file, line_num, comment = match.groups()
            comments.append({
                "path": file.strip(),
                "line": int(line_num),
                "body": comment.strip(),
            })
    return review_text, comments

# --- Post to GitHub ---
def post_comments(pr, summary, comments):
    pr.create_issue_comment(f"### 🤖 AI Review Summary\n{summary}")
    for c in comments:
        try:
            pr.create_review_comment(
                body=c["body"],
                commit_id=pr.head.sha,
                path=c["path"],
                line=c["line"]
            )
        except Exception:
            pass
    print(f"Posted {len(comments)} inline comments.")

def main():
    diff_text = fetch_pr_diff(pr)
    summary, comments = generate_review(diff_text)
    post_comments(pr, summary, comments)
    print("✅ AI PR Review Completed.")

if __name__ == "__main__":
    main()
