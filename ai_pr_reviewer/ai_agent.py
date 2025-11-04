import os, json, requests, logging, textwrap
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def generate_review(diff: str, analysis: dict):
    # Default to copilot adapter as requested
    agent_type = os.getenv('AI_AGENT_TYPE', 'copilot').lower()
    prompt = build_prompt(diff, analysis)
    if agent_type == 'copilot':
        return copilot_adapter(prompt)
    else:
        return mock_adapter(prompt)

def build_prompt(diff: str, analysis: dict) -> str:
    max_diff = 15000
    diff_slice = diff[:max_diff]
    analysis_json = json.dumps(analysis)[:12000]
    prompt = textwrap.dedent(f"""                You are an automated code-review assistant. Output JSON only with a top-level 'review' key.
        Provide a 'summary' string and 'findings' array of objects: { '{' }file, line, type, severity, message, suggestion{ '}' }.
        CODE DIFF:
        {diff_slice}

        STATIC ANALYSIS:
        {analysis_json}
        """)
    return prompt

def copilot_adapter(prompt: str):
    copilot_url = os.getenv('COPILOT_AGENT_URL')
    copilot_token = os.getenv('COPILOT_AGENT_TOKEN')
    if not copilot_url or not copilot_token:
        logger.error('COPILOT_AGENT_URL or COPILOT_AGENT_TOKEN not set; returning mock.')
        return mock_adapter(prompt)
    headers = {
        'Authorization': f'Bearer {copilot_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'ai-pr-review-agent/1.0'
    }
    payload = {'prompt': prompt, 'max_tokens': 1200}
    try:
        r = requests.post(copilot_url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # Expecting data['review'] or data['output'] containing JSON. Try to extract.
        if isinstance(data, dict) and 'review' in data:
            return data['review']
        if isinstance(data, dict) and 'output' in data:
            try:
                parsed = json.loads(data['output'])
                return parsed.get('review', parsed)
            except Exception:
                return {'summary': str(data)[:1000], 'findings': []}
        return {'summary': str(data)[:1000], 'findings': []}
    except Exception as ex:
        logger.exception('Copilot call failed')
        return {'summary': 'Copilot agent call failed: ' + str(ex), 'findings': []}

def mock_adapter(prompt: str):
    return {
        'summary': '- MOCK: No Copilot configured.',
        'findings': [
            {'file': 'src/example.py', 'line': 10, 'type': 'style', 'severity': 'low', 'message': 'Unused import', 'suggestion': 'Remove it.'}
        ]
    }
