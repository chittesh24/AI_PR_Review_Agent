# github_api.py - Authenticate as GitHub App and provide helper methods
import os, time, jwt, requests
from github import Github

def get_installation_token():
    """Create a JWT for the GitHub App and exchange it for an installation token."""
    app_id = os.getenv('APP_ID')
    installation_id = os.getenv('INSTALLATION_ID')
    private_key_path = os.getenv('PRIVATE_KEY_PATH')

    if not app_id or not installation_id or not private_key_path:
        raise EnvironmentError('APP_ID, INSTALLATION_ID and PRIVATE_KEY_PATH must be set in environment')

    with open(private_key_path, 'r') as f:
        private_key = f.read()

    now = int(time.time())
    payload = { 'iat': now - 60, 'exp': now + (9 * 60), 'iss': app_id }
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = { 'Authorization': f'Bearer {encoded_jwt}', 'Accept': 'application/vnd.github+json' }
    resp = requests.post(url, headers=headers)
    resp.raise_for_status()
    token = resp.json().get('token')
    return token

def get_installation_client():
    """Return a PyGithub Github client authenticated as the installation."""
    token = get_installation_token()
    return Github(token)

def fetch_pr_data(gh_client, owner, repo, pr_number):
    """Return list of changed files for the PR (PyGithub File objects)."""
    repo_obj = gh_client.get_repo(f"{owner}/{repo}")
    pr = repo_obj.get_pull(pr_number)
    files = list(pr.get_files())
    return files
