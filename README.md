# AI PR Review Agent (Llama via Ollama) - GitHub App Auth

This project runs an automated PR reviewer powered by a Llama model served by Ollama.
It authenticates to GitHub using a **GitHub App** (App ID + Private Key + Installation ID).
The agent runs inside Docker and connects to your local Ollama using `host.docker.internal`.

## Features
- Fetches PR diffs via GitHub App installation token
- Runs static checks (semgrep, flake8)
- Sends diff + analysis to Ollama (Llama 3)
- Posts findings as PR review comments 

## Setup (summary)
1. Install and run Ollama (in Docker or locally) and pull `llama3` model.
   Example (on host): `ollama pull llama3`
2. Create a GitHub App with required permissions (Pull requests: Read & Write)
   - Install the app into your target repo and note the **Installation ID**
   - Download the app private key (`private-key.pem`)
3. Create a `.env` file (or pass env vars to Docker). See `.env.example`.
4. Build and run the agent container:
   ```bash
   docker build -t ai-pr-review-agent .
   docker run --env-file .env -v $(pwd)/private-key.pem:/app/private-key.pem ai-pr-review-agent
   ```

## Notes
- The project **posts comments** directly to the PR by default.
- Keep your private key secure; do NOT commit it into the repository.
- Adjust semgrep/flake8 rules in `ai_pr_reviewer/analyzers.py` as needed.
