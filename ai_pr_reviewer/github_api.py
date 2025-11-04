import requests
import os

GITHUB_API = "https://api.github.com"

def fetch_pr_data(owner, repo, pr_number, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    diff_url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = requests.get(diff_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
    resp.raise_for_status()
    diff = resp.text
    meta = requests.get(diff_url, headers=headers).json()
    head_sha = meta["head"]["sha"]
    return diff, head_sha

def fetch_pr_meta(owner, repo, pr_number, token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()
