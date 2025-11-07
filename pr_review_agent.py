"""
AI PR Review Agent (OpenRouter + GPT-5 Mini)
---------------------------------------------
Automatically reviews GitHub pull requests using OpenRouter (GPT-5 Mini).

Environment Variables:
- GITHUB_TOKEN        : Provided automatically by GitHub Actions
- OPENROUTER_API_KEY  : Your OpenRouter API key (stored in GitHub Secrets)
- OPENROUTER_MODEL    : Model name (default: openai/gpt-5-mini)
- GITHUB_REPOSITORY   : e.g. chittesh24/AI_PR_Review_Agent
- PR_NUMBER           : Automatically set by workflow

Author: chittesh24
"""

import os
import re
import json
import requests
from github import Github, Auth

# --- Environment Setup ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5-mini")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("PR_NUMBER")

if not all([GITHUB_TOKEN, OPENROUTER_API_KEY, REPO_NAME, PR_NUMBER]):
    raise EnvironmentError("❌ Missing one or more required environment variables.")

# GitHub Auth (new API syntax)
gh = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = gh.get_repo(REPO_NAME)
pr = repo.get_pull(int(PR_NUMBER))


# --- Fetch PR Diff ---
def fetch_pr_diff(pr):
    """Collects changed files and diffs for the PR."""
    files = pr.get_files()
    diffs = []
    for f in files:
        if not f.patch:
            continue
        diffs.append(f"File: {f.filename}\n{f.patch}")
    return "\n\n".join(diffs)


# --- Generate Review using OpenRouter ---
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
{diff_text[:6000]}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/chittesh24/AI_PR_Review_Agent",
        "X-Title": "AI PR Review Agent",
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior developer performing PR reviews."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 800,
        "temperature": 0.4,
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code != 200:
        print("❌ OpenRouter call failed:", response.text)
        return f"❌ OpenRouter API error: {response.text}", []

    result = response.json()
    try:
        review_text = result["choices"][0]["message"]["content"]
    except Exception:
        review_text = "⚠️ No AI feedback received."

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


# --- Post Review to GitHub ---
def post_comments(pr, summary, comments):
    """Posts a summary comment and inline suggestions to the PR."""
    try:
        pr.create_issue_comment(f"### 🤖 AI Review Summary\n\n{summary}")
        print("✅ Summary comment posted.")
    except Exception as e:
        print("⚠️ Failed to post summary comment:", e)

    posted = 0
    for c in comments:
        try:
            pr.create_review_comment(
                body=c["body"],
                commit_id=pr.head.sha,
                path=c["path"],
                line=c["line"],
            )
            posted += 1
        except Exception:
            pass

    print(f"✅ Posted {posted} inline comments.")


# --- Main Execution ---
def main():
    print(f"🔍 Running AI PR Review for {REPO_NAME}#{PR_NUMBER}")
    diff_text = fetch_pr_diff(pr)
    summary, comments = generate_review(diff_text)
    post_comments(pr, summary, comments)
    print("✅ AI PR Review Completed.")


if __name__ == "__main__":
    main()
