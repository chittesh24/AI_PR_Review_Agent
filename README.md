# 🤖 AI PR Review Agent (GPT-5 Mini)
Automatically reviews Pull Requests using OpenAI GPT-5 Mini and comments on code changes.

---

## 🔧 Setup

1. Clone your repo and copy these files into it.

2. Go to your repo:
   **Settings → Secrets and variables → Actions**

3. Add the following secrets:

| Name | Example | Description |
|------|----------|-------------|
| `OPENAI_API_KEY` | `sk-xxxxx` | Your GPT-5 Mini API key |
| `GITHUB_TOKEN` | *(auto-provided)* | Used by GitHub Actions to post comments |

---

## ⚙️ Workflow

The file `.github/workflows/ai_pr_review.yml` automatically runs when:
- A PR is **opened**
- A PR is **updated**
- A PR is **reopened**

The AI agent:
1. Reads your code diff  
2. Sends it securely to GPT-5 Mini  
3. Posts a summary + inline review comments  

---

## 🧪 Optional Local Run

```bash
export GITHUB_TOKEN=ghp_xxx
export OPENAI_API_KEY=sk-xxx
export GITHUB_REPOSITORY=chittesh24/AI_PR_Review_Agent
export PR_NUMBER=1
python pr_review_agent.py

