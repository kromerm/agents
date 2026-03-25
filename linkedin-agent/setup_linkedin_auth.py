# -*- coding: utf-8 -*-
"""
LinkedIn OAuth 2.0 Setup
------------------------
Run this ONCE to connect your LinkedIn account to the agent.

    python setup_linkedin_auth.py

It will:
  1. Open your browser for LinkedIn authorization
  2. Catch the OAuth callback on http://localhost:8888/callback
  3. Exchange the code for an access token
  4. Fetch your LinkedIn profile to get your author URN
  5. Save LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN to your .env file

Prerequisites (one-time):
  - Create a LinkedIn Developer App at https://developer.linkedin.com/apps
  - Add "Sign In with LinkedIn using OpenID Connect" and "Share on LinkedIn" products
  - Set redirect URL to: http://localhost:8888/callback
  - Copy Client ID and Client Secret into .env as LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET
"""

import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key

load_dotenv(override=False)

REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "openid profile email w_member_social"
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

# Shared state between HTTP handler and main thread
_auth_result: dict = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that captures the OAuth authorization code."""

    def do_GET(self):  # noqa: N802
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            _auth_result["code"] = params["code"][0]
            _auth_result["state"] = params.get("state", [None])[0]
            body = b"<h2>Authentication successful &#10003; You can close this tab.</h2>"
            self.send_response(200)
        else:
            error = params.get("error_description", ["Unknown error"])[0]
            _auth_result["error"] = error
            body = f"<h2>Authentication failed: {error}</h2>".encode()
            self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        pass  # suppress server console output


def _start_callback_server() -> HTTPServer:
    server = HTTPServer(("localhost", 8888), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    return server


def _exchange_code_for_token(
    code: str, client_id: str, client_secret: str
) -> dict:
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _get_userinfo(access_token: str) -> dict:
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202401",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _save_to_env(key: str, value: str) -> None:
    """Create .env if it doesn't exist, then update the key."""
    if not os.path.exists(ENV_FILE):
        open(ENV_FILE, "a").close()
    set_key(ENV_FILE, key, value)


def main() -> None:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "❌  LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env\n"
            "    See README.md → 'Set up LinkedIn Developer App' for instructions."
        )
        return

    state = secrets.token_urlsafe(16)
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
        }
    )

    print("Starting LinkedIn OAuth 2.0 flow...")
    print(f"Opening browser → {auth_url}\n")

    server = _start_callback_server()
    webbrowser.open(auth_url)

    # Wait for the callback (up to 2 minutes)
    import time
    deadline = time.time() + 120
    while "code" not in _auth_result and "error" not in _auth_result:
        if time.time() > deadline:
            print("❌  Timed out waiting for LinkedIn authorization (2 min limit).")
            return
        time.sleep(0.5)

    if "error" in _auth_result:
        print(f"❌  LinkedIn authorization failed: {_auth_result['error']}")
        return

    # CSRF check
    if _auth_result.get("state") != state:
        print("❌  OAuth state mismatch — possible CSRF attempt. Aborting.")
        return

    print("✅  Authorization code received. Exchanging for access token...")

    try:
        token_data = _exchange_code_for_token(
            _auth_result["code"], client_id, client_secret
        )
    except requests.HTTPError as exc:
        print(f"❌  Token exchange failed: {exc}\n{exc.response.text if exc.response else ''}")
        return

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", "?")

    print("✅  Access token obtained.")
    print(f"    Expires in: {int(expires_in) // 86400} days\n")
    print("Fetching your LinkedIn profile...")

    try:
        profile = _get_userinfo(access_token)
    except requests.HTTPError as exc:
        print(f"❌  Could not fetch profile: {exc}")
        return

    person_id = profile.get("sub")
    author_urn = f"urn:li:person:{person_id}"
    name = profile.get("name", "Unknown")
    email = profile.get("email", "")

    _save_to_env("LINKEDIN_ACCESS_TOKEN", access_token)
    _save_to_env("LINKEDIN_AUTHOR_URN", author_urn)

    print(f"✅  Authenticated as: {name} ({email})")
    print(f"    Author URN : {author_urn}")
    print("    Saved LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN to .env\n")
    print("🚀  You're all set! Run  python main.py  to start the agent.")


if __name__ == "__main__":
    main()
