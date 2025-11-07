# AI PR Review Agent (OpenRouter + GPT-5 Mini default)

This repository contains a GitHub Actions-based PR reviewer that:
- Fetches a PR diff
- Runs Semgrep + pip-audit for static & dependency checks
- Sends a combined prompt to OpenRouter (configurable model)
- Posts a summary and inline comments back to the PR

## Setup

1. Add secrets to your repository (Settings → Secrets and variables → Actions):
   - `OPENROUTER_API_KEY` : your OpenRouter API key (sk-or-...)
   - (optional) `OPENROUTER_MODEL` : override default model (e.g. openai/gpt-5-mini)

2. The workflow is configured to run on pull_request events. No manual triggers needed.

3. Ensure the repository has `requirements.txt` at root if you want pip-audit to run.

## Notes & Troubleshooting
- The agent posts a summary comment and inline review comments (when output parsed as FILE:LINE - Comment).
- If OpenRouter key hits quota, create a new key or upgrade plan on OpenRouter.
- Semgrep runs against patch text (best-effort); for more accurate results, consider checking out full repo.

