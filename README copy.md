# AI PR Review Agent (Copilot SDK Integration)

This repository contains an example AI PR Review Agent that runs as a GitHub Action when a Pull Request is opened or updated.
It performs static analysis, builds a prompt from the diff and analysis output, sends the prompt to a **Copilot Agent** endpoint, and posts results back to the PR as a GitHub Check Run (with annotations) and a PR review comment.

## Features
- Trigger on pull_request events
- Fetch PR diff and metadata
- Run quick static analysis (flake8; you can add semgrep/pip-audit)
- Build a prompt and call Copilot Agent SDK/endpoint (placeholder HTTP call)
- Post results as Check Run annotations and PR review comment

## Secrets to configure (GitHub repository or organization secrets)
- `GITHUB_TOKEN` (provided by GitHub Actions automatically)
- `COPILOT_AGENT_URL` (your Copilot Agent HTTP endpoint)
- `COPILOT_AGENT_TOKEN` (token for the Copilot Agent)
- Optionally: `AI_AGENT_TYPE` (defaults to `copilot` in the workflow)

## How to use
1. Add this repo to your organization or fork.
2. Add the required secrets in GitHub (see above).
3. Customize `.ai-pr-review.yml` if desired (repo-level config).
4. Open a PR — the Action will run and post an automated review.

## Notes
- The copilot adapter in `ai_pr_reviewer/ai_agent.py` uses a generic HTTP POST to `COPILOT_AGENT_URL`. Replace that with your organization's Copilot SDK client if available.
- **Do not** send secrets or private keys to third-party services. Use an internal, approved Copilot Agent for private repositories.
