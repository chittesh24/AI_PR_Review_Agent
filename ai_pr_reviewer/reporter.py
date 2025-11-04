import requests, math

GITHUB_API = 'https://api.github.com'

def create_check_with_annotations(owner, repo, head_sha, name, summary, findings, token):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/check-runs"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    annotations = []
    for f in findings:
        level = 'notice'
        if f.get('severity') == 'high':
            level = 'failure'
        elif f.get('severity') == 'medium':
            level = 'warning'
        annotations.append({
            'path': f.get('file', ''),
            'start_line': f.get('line') or 1,
            'end_line': f.get('line') or 1,
            'annotation_level': level,
            'message': f"{f.get('type')}: {f.get('message')}",
            'title': f.get('type', 'issue')
        })

    batch_size = 40
    total_batches = math.ceil(len(annotations) / batch_size) or 1

    # Create initial in_progress check run
    initial_payload = {'name': name, 'head_sha': head_sha, 'status': 'in_progress'}
    r = requests.post(url, headers=headers, json=initial_payload)
    r.raise_for_status()
    check_run = r.json()
    check_run_id = check_run['id']

    for i in range(total_batches):
        batch = annotations[i*batch_size:(i+1)*batch_size]
        out = {'title': name, 'summary': summary if i == total_batches - 1 else '', 'annotations': batch}
        update_url = f"{GITHUB_API}/repos/{owner}/{repo}/check-runs/{check_run_id}"
        status = 'completed' if i == total_batches - 1 else 'in_progress'
        conclusion = 'neutral'
        payload = {'output': out, 'status': status, 'conclusion': conclusion}
        resp = requests.patch(update_url, headers=headers, json=payload)
        resp.raise_for_status()
    return check_run

def post_review_comment(owner, repo, pr_number, summary, token):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    body = summary or 'AI PR Review: no summary generated.'
    requests.post(url, headers=headers, json={'body': body, 'event': 'COMMENT'})
