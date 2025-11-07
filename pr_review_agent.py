"""
AI PR Review Agent (OpenRouter + GPT-5 Mini + Static Analysis)
---------------------------------------------------------------
Automatically reviews GitHub pull requests using OpenRouter and static analysis.

Features:
- Fetches code diff from GitHub PR
- Runs static analysis with Semgrep and pip-audit
- Generates AI-based code review summary and inline feedback
- Posts comments directly on the PR

Environment Variables:
- GITHUB_TOKEN        : Provided automatically by GitHub Actions
- OPENROUTER_API_KEY  : Your OpenRouter API key (in GitHub Secrets)
- OPENROUTER_MODEL    : Model name (default: openai/gpt-5-mini)
- GITHUB_REPOSITORY   : e.g. chittesh24/AI_PR_Review_Agent
- PR_NUMBER           : Automatically set by GitHub workflow
"""

import os
import re
import json
import subprocess
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

# GitHub authentication
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


# --- Run Static Analysis ---
def run_static_analysis():
    """Runs Semgrep and pip-audit, returns summarized findings."""
    findings = []

    # Run Semgrep
    try:
        print("🔍 Running Semgrep...")
        semgrep_result = subprocess.run(
            ["semgrep", "--config", "auto", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if semgrep_result.stdout:
            sg_json = json.loads(semgrep_result.stdout)
            for r in sg_json.get("results", []):
                findings.append(
                    f"[Semgrep] {r.get('path', '')}:{r.get('start', {}).get('line', 0)} - {r.get('extra', {}).get('message', '')}"
                )
    except Exception as e:
        findings.append(f"[Semgrep Error] {e}")

    # Run pip-audit
    try:
        print("📦 Running pip-audit...")
        pip_audit = subprocess.run(
            ["pip-audit", "-f", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if pip_audit.stdout:
            pa_json = json.loads(pip_audit.stdout)
            for pkg in pa_json:
                findings.append(
                    f"[pip-audit] {pkg['name']}=={pkg['version']} - {pkg['vulns'][0]['id'] if pkg.get('vulns') else 'No vulnerabilities'}"
                )
    except Exception as e:
        findings.append(f"[pip-audit Error] {e}")

    return "\n".join(findings[:50]) or "No major static issues found."


# --- Generate Review using OpenRouter ---
def generate_review(diff_text, static_analysis):
    prompt = f"""
You are an expert software engineer reviewing a GitHub Pull Request.

Review the following code changes and provide:
1. A summary comment of overall quality.
2. Line-by-line feedback (FILE:LINE - Comment).
3. Include any static analysis findings relevance.

Code diff:
{diff_text[:5000]}

Static analysis results:
{static_analysis[:2000]}
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
        "max_tokens": 900,
        "temperature": 0.3,
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
    print(f"🚀 Running AI PR Review for {REPO_NAME}#{PR_NUMBER}")

    diff_text = fetch_pr_diff(pr)
    print("📄 Diff fetched.")

    static_analysis = run_static_analysis()
    print("🔧 Static analysis complete.")

    summary, comments = generate_review(diff_text, static_analysis)
    print("🧠 AI review generated.")

    post_comments(pr, summary, comments)
    print("✅ AI PR Review Completed.")


if __name__ == "__main__":
    main()
