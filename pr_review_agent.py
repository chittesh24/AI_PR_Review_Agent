# pr_review_agent.py
"""AI PR Review Agent (OpenRouter + GPT-5-mini by default)

Behavior:
- Triggered by GitHub Actions on pull_request events
- Fetches PR diff via GitHub API
- Runs Semgrep and pip-audit (if requirements.txt present)
- Sends diff + analysis to OpenRouter (configurable model)
- Posts summary comment + inline review comments to PR

Env variables expected (provided by workflow):
- GITHUB_TOKEN (auto by GitHub Actions)
- OPENROUTER_API_KEY (repo secret)
- GITHUB_REPOSITORY (e.g. owner/repo)
- PR_NUMBER (pull request number)
- OPENROUTER_MODEL (optional, default: openai/gpt-5-mini)
"""
import os
import re
import json
import subprocess
import requests
from github import Github, Auth

# --- config from env ---
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
REPO_FULL = os.getenv('GITHUB_REPOSITORY')
PR_NUMBER = os.getenv('PR_NUMBER')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-5-mini')

if not all([GITHUB_TOKEN, OPENROUTER_API_KEY, REPO_FULL, PR_NUMBER]):
    raise EnvironmentError('Missing required environment variables. Make sure GITHUB_TOKEN, OPENROUTER_API_KEY, GITHUB_REPOSITORY and PR_NUMBER are set.')

owner, repo_name = REPO_FULL.split('/')

# Github client
gh = Github(auth=Auth.Token(GITHUB_TOKEN))
repo = gh.get_repo(REPO_FULL)
pr = repo.get_pull(int(PR_NUMBER))

OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'

# --- helper: fetch PR files/diffs
def fetch_pr_files(pr):
    files = list(pr.get_files())
    return files

# --- static analysis ---
def run_semgrep_on_patch(patch_text):
    issues = []
    try:
        import tempfile, os as _os
        with tempfile.NamedTemporaryFile(delete=False, suffix='.diff', mode='w') as tf:
            tf.write(patch_text)
            tmpname = tf.name
        # run semgrep on the temp file (best-effort)
        res = subprocess.run(['semgrep', '--config', 'auto', '--json', tmpname],
                             capture_output=True, text=True, timeout=60)
        if res.stdout:
            data = json.loads(res.stdout)
            for r in data.get('results', []):
                issues.append({
                    'tool': 'semgrep',
                    'file': r.get('path') or r.get('extra', {}).get('metadata', {}).get('path', '<unknown>'),
                    'line': r.get('start', {}).get('line', 1),
                    'message': r.get('extra', {}).get('message', '')
                })
        try:
            _os.remove(tmpname)
        except Exception:
            pass
    except Exception as e:
        print('semgrep error:', e)
    return issues

def run_pip_audit_if_present(repo_dir):
    issues = []
    # only run pip-audit if requirements.txt exists in checked out repo
    req_path = os.path.join(repo_dir, 'requirements.txt')
    if not os.path.exists(req_path):
        return issues
    try:
        res = subprocess.run(['pip-audit', '-r', req_path, '--format', 'json'],
                             capture_output=True, text=True, timeout=120)
        if res.stdout:
            data = json.loads(res.stdout)
            vulns = data.get('vulnerabilities') if isinstance(data, dict) else data
            if vulns:
                for v in vulns:
                    issues.append({
                        'tool': 'pip-audit',
                        'file': 'requirements.txt',
                        'line': 1,
                        'message': f"{v.get('package') or v.get('name')} {v.get('version','')}: {v.get('description', '')[:200]}"
                    })
    except Exception as e:
        print('pip-audit error:', e)
    return issues

# --- build prompt ---
def build_prompt(diff_text, analysis):
    analysis_text = '\n'.join([f"[{a.get('tool')}] {a.get('file')}:{a.get('line')} - {a.get('message')}" for a in analysis]) or 'No static analysis issues found.'
    prompt = f"""You are a senior software engineer reviewing a GitHub Pull Request.

Provide:
1) A short summary of the PR.
2) Line-by-line comments formatted as: FILE:LINE - Comment
3) Security and dependency concerns called out clearly.

DIFF:
{diff_text}

STATIC ANALYSIS FINDINGS:
{analysis_text}

ONLY output comments in the format 'FILE:LINE - Comment' (one per line). Precede with a short summary header.
"""
    return prompt

# --- call OpenRouter ---
def call_openrouter(prompt, model):
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a senior software engineer performing code reviews.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.0,
        'max_tokens': 1200
    }
    resp = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f'OpenRouter API error {resp.status_code}: {resp.text}')
    data = resp.json()
    text = ''
    try:
        text = data.get('choices', [])[0].get('message', {}).get('content', '') or data.get('output') or ''
    except Exception:
        text = json.dumps(data)
    return text

# --- parse model output into findings ---
def parse_findings(text):
    findings = []
    summary_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^([^:]+):(\d+)\s*-\s*(.+)$', line)
        if m:
            path, ln, msg = m.groups()
            findings.append({'file': path.strip(), 'line': int(ln), 'message': msg.strip()})
        else:
            summary_lines.append(line)
    summary = '\n'.join(summary_lines[:20])
    return summary, findings

# --- post comments ---
def post_summary_and_inline(pr, summary, findings):
    try:
        pr.create_issue_comment(f"### 🤖 AI Review Summary\n\n{summary}")
    except Exception as e:
        print('Failed to post summary comment:', e)
    if not findings:
        return
    latest_commit = list(pr.get_commits())[-1]
    for f in findings:
        try:
            pr.create_review_comment(body=f.get('message'), commit_id=latest_commit.sha, path=f.get('file'), line=f.get('line'))
        except Exception as e:
            print('Failed posting inline comment for', f, e)

def main():
    print(f"Running AI PR Review for {REPO_FULL}#{PR_NUMBER}")
    files = fetch_pr_files(pr)
    print('Files changed count:', len(files))
    # create combined diff (truncate to safe length)
    diff_text = "\n\n".join([f"FILE: {f.filename}\n" + (f.patch or '') for f in files])[:25000]

    # run semgrep on each patch (best effort)
    analysis = []
    for f in files:
        if f.patch:
            analysis.extend(run_semgrep_on_patch(f.patch))

    # clone repo to workspace to run pip-audit if requirements exists
    repo_dir = '/tmp/repo_checkout'
    try:
        import shutil
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        # shallow clone only changed files not necessary; clone full repo for pip-audit
        subprocess.run(['git', 'clone', '--depth', '1', f'https://github.com/{REPO_FULL}.git', repo_dir], check=True, capture_output=True, text=True)
    except Exception as e:
        print('Git clone failed (pip-audit may be skipped):', e)

    analysis.extend(run_pip_audit_if_present(repo_dir))
    print('Static analysis findings:', len(analysis))

    prompt = build_prompt(diff_text, analysis)
    print('Calling OpenRouter with model', OPENROUTER_MODEL)
    try:
        text = call_openrouter(prompt, OPENROUTER_MODEL)
    except Exception as e:
        print('OpenRouter call failed:', e)
        text = 'OpenRouter call failed: ' + str(e)

    summary, findings = parse_findings(text)
    print('AI summary:', summary[:300])
    print('AI findings count:', len(findings))

    post_summary_and_inline(pr, summary, findings)
    print('Done.')

if __name__ == '__main__':
    main()
