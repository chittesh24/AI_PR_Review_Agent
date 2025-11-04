# analyzers.py - run simple static checks (semgrep, flake8)
import subprocess, json, os, tempfile

def run_semgrep_on_patch(patch_text):
    # semgrep expects files; we'll write a temp file with the patch (best-effort)
    issues = []
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.diff', mode='w') as tf:
            tf.write(patch_text)
            tmpname = tf.name
        result = subprocess.run(['semgrep', '--config', 'auto', '--json', tmpname],
                                capture_output=True, text=True, timeout=60)
        if result.stdout:
            data = json.loads(result.stdout)
            for r in data.get('results', []):
                issues.append({
                    'tool': 'semgrep',
                    'file': r.get('path') or r.get('extra', {}).get('metadata', {}).get('path', '<unknown>'),
                    'line': r.get('start', {}).get('line', 1),
                    'message': r.get('extra', {}).get('message', '')
                })
    except Exception as ex:
        print('semgrep error:', ex)
    return issues

def run_flake8_on_patch(patch_text):
    # flake8 works best on files; we can run flake8 on repo in container if checked out.
    issues = []
    try:
        result = subprocess.run(['flake8', '--format', 'json', '.'],
                                capture_output=True, text=True, timeout=60)
        if result.stdout:
            data = json.loads(result.stdout)
            for fname, entries in data.items():
                for e in entries:
                    issues.append({
                        'tool': 'flake8',
                        'file': fname,
                        'line': e.get('line_number', 1),
                        'message': e.get('text', '')
                    })
    except Exception as ex:
        print('flake8 error:', ex)
    return issues

def run_static_analysis(files):
    """files: list of PyGithub File objects (have .filename and .patch)"""
    all_issues = []
    for f in files:
        patch = f.patch or ''
        # Run semgrep on patch (best-effort)
        all_issues.extend(run_semgrep_on_patch(patch))
    # Try a repo-wide flake8 if available
    all_issues.extend(run_flake8_on_patch(''))
    return all_issues
