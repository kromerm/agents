# -*- coding: utf-8 -*-
"""
LinkedIn Post Agent
-------------------
An interactive AI agent that generates and publishes professional LinkedIn posts.
Uses Azure AI Foundry for intelligent content generation and the LinkedIn API for posting.

Run: python main.py
Then open the AI Toolkit Agent Inspector (VS Code) or press F5 with the debug config.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=False)

from agent_framework.observability import configure_otel_providers
from agent_framework.azure import AzureAIClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity.aio import DefaultAzureCredential

from linkedin_tools import post_to_linkedin, get_post_preview, check_linkedin_status

configure_otel_providers(
    vs_code_extension_port=4317,
    enable_sensitive_data=True,
)

AGENT_INSTRUCTIONS = """
You are a professional LinkedIn content creator and social media assistant.
Your job is to help the user craft and publish high-quality, engaging LinkedIn posts.

## Your capabilities
- Generate professional LinkedIn posts on any topic
- Preview posts before they go live
- Publish posts directly to LinkedIn
- Refine drafts based on user feedback

## LinkedIn post best practices you ALWAYS follow
- Open with a compelling hook (question, surprising stat, or bold statement)
- Write in a professional yet authentic, personable tone
- Use 3–5 relevant hashtags at the end
- Keep posts under 1,500 characters for best engagement (hard limit: 3,000 chars)
- Use line breaks generously for readability
- Mirror the user's voice — ask about their tone/style if unclear
- Include a call-to-action at the end (e.g., "What do you think?", "Drop a comment below")
- Use emojis sparingly and only where they add value

## Standard workflow
1. Ask the user what they want to post about (topic, key points, tone, target audience)
2. Ask clarifying questions if the brief is vague
3. Generate 1–2 draft options
4. Show a preview using get_post_preview
5. Refine based on feedback
6. Ask for explicit confirmation ("Shall I publish this?") before calling post_to_linkedin
7. Report the outcome

## Important rules
- NEVER call post_to_linkedin without explicit user approval
- Always use check_linkedin_status if you suspect auth issues
- If the user says "post it" / "go ahead" / "publish it" — that counts as approval
- Keep track of previous drafts in the conversation so you can compare/iterate
"""


async def _run_agent(credential) -> None:
    async with AzureAIClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model_deployment_name=os.environ.get("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4o"),
        credential=credential,
    ).as_agent(
        name="linkedin-post-agent",
        instructions=AGENT_INSTRUCTIONS,
        tools=[check_linkedin_status, get_post_preview, post_to_linkedin],
    ) as agent:
        print("✅ LinkedIn Post Agent is running on http://localhost:8088")
        print("   Open VS Code AI Toolkit → Agent Inspector to start chatting.")
        print("   Press Ctrl+C to stop.\n")
        await from_agent_framework(agent).run_async()


async def main() -> None:
    project_endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")

    if not project_endpoint:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT is not set. "
            "Copy .env.template to .env and fill in the values."
        )

    # AzureAIClient requires an async token credential with get_token().
    # If your Foundry resource is in a different tenant than your default az login,
    # set AZURE_TENANT_ID in .env — DefaultAzureCredential reads it automatically.
    # Then run: az login --tenant <AZURE_TENANT_ID>
    async with DefaultAzureCredential() as credential:
        await _run_agent(credential)


if __name__ == "__main__":
    asyncio.run(main())
