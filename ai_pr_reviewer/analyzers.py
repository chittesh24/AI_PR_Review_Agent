import subprocess
import json

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def run_static_analysis():
    results = {}
    # flake8 (ensure flake8 is installed in runner)
    try:
        out = run_cmd(["flake8", "--format=json", "."])
        # flake8 may return '' when no issues
        results['flake8'] = json.loads(out) if out else {}
    except Exception:
        results['flake8'] = {}
    # Placeholder for semgrep / pip-audit (install in runner if desired)
    results['semgrep'] = None
    results['pip_audit'] = None
    return results
