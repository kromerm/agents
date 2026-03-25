# LinkedIn Post Agent

An interactive AI agent that helps you craft and publish professional LinkedIn posts. Powered by Azure AI Foundry (GPT-4o) and the Microsoft Agent Framework.

## What it does

Chat with the agent to:
- **Generate** polished, professional LinkedIn posts on any topic
- **Preview** drafts before they go live  
- **Iterate** on drafts based on your feedback
- **Publish** directly to your LinkedIn profile with one confirmation

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` |
| Azure AI Foundry project | Already configured (`markkromer-linkedin`) |
| LinkedIn Developer App | One-time setup — see below |
| VS Code + [AI Toolkit extension](https://marketplace.visualstudio.com/items?itemName=ms-windows-ai-studio.windows-ai-studio) | For the Agent Inspector UI |

---

## Setup

### 1. Create a virtual environment and install dependencies

```bash
cd linkedin-agent

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install --pre agent-dev-cli  # agentdev CLI for local debugging
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.template` to `.env` (already done — `.env` is pre-populated with your Azure details):

```bash
copy .env.template .env     # if you need to recreate it
```

Your `.env` already contains:
- `FOUNDRY_PROJECT_ENDPOINT` — your Azure AI Foundry endpoint
- `AZURE_AI_API_KEY` — your API key (**rotate this key** — it was shared in chat)
- `FOUNDRY_MODEL_DEPLOYMENT_NAME` — set to `gpt-4o` (update if your deployment differs)

> ⚠️ **Security:** Your API key was discussed in chat. Please rotate it at [ai.azure.com](https://ai.azure.com) → your project → Settings → API keys, then update `.env`.

### 3. Set up your LinkedIn Developer App (one-time)

1. Go to [developer.linkedin.com/apps](https://developer.linkedin.com/apps) → **Create app**
2. Fill in app name, your LinkedIn page, and logo
3. On the **Products** tab, request access to:
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
4. On the **Auth** tab:
   - Copy **Client ID** and **Client Secret** into `.env`
   - Under *OAuth 2.0 Settings*, add redirect URL: `http://localhost:8888/callback`

### 4. Authenticate with LinkedIn

```bash
python setup_linkedin_auth.py
```

This opens your browser, completes the OAuth flow, and saves `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_AUTHOR_URN` to `.env`.

> **Token expiry:** LinkedIn tokens last ~60 days. Re-run `setup_linkedin_auth.py` when they expire.

---

## Running the Agent

### Option A — VS Code (recommended)

1. Open the `linkedin-agent` folder in VS Code
2. Press **F5** → select **"Debug LinkedIn Post Agent (HTTP Server)"**
3. The AI Toolkit **Agent Inspector** opens automatically in the browser
4. Chat with the agent!

### Option B — Terminal

```bash
.venv\Scripts\activate
python main.py
```

Then open: [http://localhost:8088](http://localhost:8088)

Or send a test message via curl:
```bash
curl -X POST http://localhost:8088/openai/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"linkedin-post-agent","input":"Help me write a post about building AI agents with Azure"}'
```

---

## Example Conversations

**Starting a post from scratch:**
```
You:   Write a LinkedIn post about my team shipping a new AI feature last week
Agent: What was the feature? Who's your audience — developers, PMs, or general?
You:   It's an intelligent search feature for our enterprise app. Audience: tech leaders.
Agent: Here's a draft... [shows preview]
You:   Love it, publish it!
Agent: 🎉 Post published! View at https://www.linkedin.com/feed/update/...
```

**Giving a detailed brief:**
```
You:   Post about Azure AI — professional tone, 5 hashtags, include a CTA
       Key points: faster inference, cost savings, Copilot integration
Agent: [generates post, shows preview]
You:   Change "faster" to "10x faster" and make the opening punchier
Agent: [revised preview]
You:   Perfect, go ahead
```

---

## Project Structure

```
linkedin-agent/
├── main.py                  # Agent entry point
├── linkedin_tools.py        # LinkedIn API tools (post, preview, status check)
├── setup_linkedin_auth.py   # One-time LinkedIn OAuth setup
├── requirements.txt
├── .env                     # Secrets (gitignored)
├── .env.template            # Template — safe to commit
├── .gitignore
├── .foundry/
│   └── agent-metadata.yaml  # Foundry project metadata
└── .vscode/
    ├── launch.json          # Debug configurations
    └── tasks.json           # Debug tasks (agentdev + Agent Inspector)
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `FOUNDRY_PROJECT_ENDPOINT is not set` | Check `.env` exists and has the endpoint |
| `401 Unauthorized` from Azure AI | Rotate your API key and update `.env` |
| `LinkedIn is NOT authenticated` | Run `python setup_linkedin_auth.py` |
| `LinkedIn token is expired` | Re-run `python setup_linkedin_auth.py` |
| `ModuleNotFoundError: agent_framework` | Run `pip install -r requirements.txt` in `.venv` |
| Port 8088 already in use | Kill existing process: `netstat -ano \| findstr 8088` then `taskkill /PID <pid> /F` |

---

## Security Notes

- `.env` is gitignored — never commit it
- Rotate your Azure AI API key after this initial setup
- LinkedIn OAuth tokens last ~60 days and are scoped to `w_member_social` only
- The agent always asks for confirmation before posting to LinkedIn
