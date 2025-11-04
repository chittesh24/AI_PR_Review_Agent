# ai_agent.py - Send prompt to Ollama (Llama3) via HTTP API (host.docker.internal)
import os, requests, json, textwrap

OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')

def build_prompt(diff_text, analysis):
    analysis_text = '\n'.join([f"[{a.get('tool')}] {a.get('file')}:{a.get('line')} - {a.get('message')}" for a in analysis])
    prompt = textwrap.dedent(f"""You are a senior software engineer doing a PR review.

        Review the following code changes and static analysis findings.
        Provide concise, actionable comments in the format: FILE:LINE - Comment

        DIFF:
        {diff_text}

        STATIC ANALYSIS:
        {analysis_text}

        Only output comments, one per line, formatted as: FILE:LINE - Comment
        """)
    return prompt

def generate_review(diff_text, analysis):
    prompt = build_prompt(diff_text, analysis)[:30000]
    payload = {
        'model': OLLAMA_MODEL,
        'prompt': prompt,
        'max_tokens': 1024,
        'temperature': 0.0,
        'stream': False
    }
    try:
        resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        # Ollama response shape may vary; try common keys
        text = data.get('response') or data.get('output') or ''
        if not text and isinstance(data, dict):
            # if response is nested
            text = json.dumps(data)
        # Parse lines into findings
        findings = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Expected format: path:line - message
            parts = line.split('-', 1)
            if len(parts) != 2:
                continue
            left, msg = parts
            if ':' in left:
                filepart, lineno = left.rsplit(':', 1)
                try:
                    lineno = int(lineno.strip())
                except:
                    lineno = 1
                findings.append({'file': filepart.strip(), 'line': lineno, 'type': 'ai', 'severity': 'medium', 'message': msg.strip()})
        return {'summary': text, 'findings': findings}
    except Exception as ex:
        return {'summary': f'Ollama request failed: {ex}', 'findings': []}
