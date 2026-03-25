# -*- coding: utf-8 -*-
"""
LinkedIn Tools
--------------
Function tools exposed to the LinkedIn Post Agent.
All API credentials are read from environment variables (set in .env).
"""

import os
from typing import Annotated

import requests

_LINKEDIN_API = "https://api.linkedin.com"
_LINKEDIN_VERSION = "202501"
_MAX_POST_CHARS = 3000


def _get_headers(versioned: bool = False) -> dict:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip().strip("'")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    if versioned:
        headers["LinkedIn-Version"] = _LINKEDIN_VERSION
    return headers


# ─────────────────────────────────────────────────────────────────────────────
# Tool: check_linkedin_status
# ─────────────────────────────────────────────────────────────────────────────

def check_linkedin_status() -> str:
    """
    Check whether LinkedIn authentication is configured and return the connected
    profile name. Call this at the start of a session or when auth issues arise.
    """
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.environ.get("LINKEDIN_AUTHOR_URN")

    if not access_token:
        return (
            "⚠️  LinkedIn is NOT authenticated.\n"
            "Please run: python setup_linkedin_auth.py\n"
            "Then restart the agent so the new token is loaded."
        )

    try:
        resp = requests.get(
            f"{_LINKEDIN_API}/v2/userinfo",
            headers=_get_headers(versioned=True),
            timeout=10,
        )
        resp.raise_for_status()
        profile = resp.json()
        name = profile.get("name", "Unknown")
        email = profile.get("email", "")
        return (
            f"✅ LinkedIn authenticated.\n"
            f"   Name : {name}\n"
            f"   Email: {email}\n"
            f"   URN  : {author_urn or '⚠️  not set — re-run setup_linkedin_auth.py'}"
        )
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 401:
            return (
                "❌ LinkedIn token is expired or invalid.\n"
                "Re-run: python setup_linkedin_auth.py"
            )
        return f"❌ LinkedIn API error (HTTP {status}): {exc}"
    except requests.RequestException as exc:
        return f"❌ Network error reaching LinkedIn: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Tool: get_post_preview
# ─────────────────────────────────────────────────────────────────────────────

def get_post_preview(
    content: Annotated[str, "The full text of the LinkedIn post draft to preview"],
) -> str:
    """
    Return a formatted preview of a LinkedIn post draft, including character
    count and a readability check. Always call this before post_to_linkedin so
    the user can review the final text.
    """
    char_count = len(content)
    line_count = content.count("\n") + 1
    within_limit = char_count <= _MAX_POST_CHARS
    status_icon = "✅" if within_limit else "❌"

    separator = "─" * 52
    preview = (
        f"\n📄 POST PREVIEW\n"
        f"{separator}\n"
        f"{content}\n"
        f"{separator}\n"
        f"📊 {char_count}/{_MAX_POST_CHARS} chars  |  {line_count} lines  |  "
        f"{status_icon} {'OK' if within_limit else 'TOO LONG — trim before posting'}\n"
    )
    return preview


# ─────────────────────────────────────────────────────────────────────────────
# Tool: post_to_linkedin
# ─────────────────────────────────────────────────────────────────────────────

def post_to_linkedin(
    content: Annotated[
        str,
        "The final, approved text to publish as a LinkedIn post. "
        "Must be under 3,000 characters.",
    ],
) -> str:
    """
    Publish a text post to the user's LinkedIn profile. Only call this after the
    user has explicitly approved the draft. Returns a success message with the
    post ID, or an error description.
    """
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip().strip("'")
    author_urn = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip().strip("'")

    if not access_token:
        return (
            "❌ Cannot post: LinkedIn access token is missing.\n"
            "Run: python setup_linkedin_auth.py"
        )
    if not author_urn:
        return (
            "❌ Cannot post: LinkedIn author URN is missing.\n"
            "Run: python setup_linkedin_auth.py"
        )
    if len(content) > _MAX_POST_CHARS:
        return (
            f"❌ Post is {len(content)} characters — exceeds the {_MAX_POST_CHARS}-char limit.\n"
            "Please shorten it before publishing."
        )
    if not content.strip():
        return "❌ Post content is empty. Please provide text to publish."

    author_urn_clean = author_urn  # already stripped above
    payload = {
        "author": author_urn_clean,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        resp = requests.post(
            f"{_LINKEDIN_API}/v2/ugcPosts",
            headers=_get_headers(),
            json=payload,
            timeout=20,
        )

        if resp.status_code == 201:
            post_id = resp.json().get("id") or resp.headers.get("x-restli-id", "unknown")
            post_url = f"https://www.linkedin.com/feed/update/{post_id}/"
            return (
                f"🎉 Post published successfully!\n"
                f"   Post ID : {post_id}\n"
                f"   View at : {post_url}"
            )

        # Surface useful error details
        try:
            err_body = resp.json()
            err_msg = (
                err_body.get("message")
                or err_body.get("errorDetailedMessage")
                or resp.text
            )
        except Exception:
            err_msg = resp.text

        return f"❌ LinkedIn API error (HTTP {resp.status_code}): {err_msg}"

    except requests.RequestException as exc:
        return f"❌ Network error when posting to LinkedIn: {exc}"
