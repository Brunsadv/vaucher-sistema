"""
Google OAuth Module for Vaucher e Alvares System
Handles Google authentication flow for both admin and client portals.
"""

import secrets
from typing import Optional
from urllib.parse import urlencode
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests

from modules.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI_ADMIN,
    GOOGLE_REDIRECT_URI_CLIENTE,
    logger
)

# In-memory state store for CSRF protection
_state_store = {}


def generate_oauth_state(user_type: str) -> str:
    """Generate a secure state parameter for CSRF protection."""
    state = secrets.token_urlsafe(32)
    _state_store[state] = user_type
    return state


def validate_oauth_state(state: str) -> Optional[str]:
    """Validate state and return user_type, or None if invalid."""
    return _state_store.pop(state, None)


def get_google_auth_url(user_type: str = "admin") -> str:
    """Generate Google OAuth authorization URL."""
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured")
        return None

    state = generate_oauth_state(user_type)
    redirect_uri = GOOGLE_REDIRECT_URI_ADMIN if user_type == "admin" else GOOGLE_REDIRECT_URI_CLIENTE

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"
    }

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def verify_google_token(code: str, user_type: str = "admin") -> Optional[dict]:
    """
    Exchange authorization code for tokens and verify the ID token.
    Returns user info dict with email, name, google_id, or None if invalid.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth credentials not configured")
        return None

    redirect_uri = GOOGLE_REDIRECT_URI_ADMIN if user_type == "admin" else GOOGLE_REDIRECT_URI_CLIENTE

    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )

        if response.status_code != 200:
            logger.error(f"Google token exchange failed: {response.status_code} - {response.text}")
            return None

        tokens = response.json()

        if "id_token" not in tokens:
            logger.error("No id_token in Google response")
            return None

        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            tokens["id_token"],
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        return {
            "google_id": idinfo["sub"],
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
            "email_verified": idinfo.get("email_verified", False)
        }
    except Exception as e:
        logger.error(f"Google token verification failed: {e}")
        return None
