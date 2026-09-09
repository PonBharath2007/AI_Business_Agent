import os
import urllib.parse
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import requests
import jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from backend.app.models.models import User, Business
from backend.app.auth.jwt import JWT_SECRET, JWT_ALGORITHM
from backend.app.utils.logger import logger
from backend.app.services.activity_service import log_activity

load_dotenv()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

def get_google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()

def get_google_client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

def is_google_auth_configured() -> bool:
    """
    Checks if Google OAuth credentials are provided in environment variables.
    """
    client_id = get_google_client_id()
    client_secret = get_google_client_secret()
    return bool(client_id and client_secret and len(client_id) > 10)

def get_redirect_uri(custom_uri: Optional[str] = None) -> str:
    if custom_uri and custom_uri.strip():
        return custom_uri.strip()
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback").strip()

def get_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")

def generate_oauth_state() -> str:
    """
    Generates a cryptographically signed state token with a 15-minute expiration
    to prevent CSRF attacks during the OAuth 2.0 flow.
    """
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "type": "oauth_state",
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_oauth_state(state: Optional[str]) -> bool:
    """
    Validates the CSRF state token returned by Google during callback.
    """
    if not state or not state.strip():
        return False
    try:
        payload = jwt.decode(state.strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("type") == "oauth_state"
    except Exception as exc:
        logger.warning(f"Google OAuth state validation failed: {exc}")
        return False

def build_google_auth_url(state: Optional[str] = None, redirect_uri: Optional[str] = None) -> str:
    """
    Generates the Google OAuth 2.0 consent screen redirect URL with proper OpenID Connect scopes.
    """
    client_id = get_google_client_id()
    target_redirect = get_redirect_uri(redirect_uri)
    oauth_state = state or generate_oauth_state()

    params = {
        "client_id": client_id,
        "redirect_uri": target_redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": oauth_state,
        "prompt": "select_account"
    }

    query_string = urllib.parse.urlencode(params)
    return f"{GOOGLE_AUTH_URL}?{query_string}"

def exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchanges authorization code for Google access token and ID token.
    Google Client Secret is used exclusively here on the backend.
    """
    client_id = get_google_client_id()
    client_secret = get_google_client_secret()
    target_redirect = get_redirect_uri(redirect_uri)

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": target_redirect,
        "grant_type": "authorization_code"
    }

    try:
        response = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Google token exchange failed ({response.status_code}): {response.text}")
            return {"error": f"Token exchange failed with status {response.status_code}"}
        return response.json()
    except Exception as e:
        logger.error(f"Error during Google token exchange: {e}")
        return {"error": str(e)}

def fetch_google_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetches verified user profile information from Google UserInfo endpoint using Bearer token.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch Google userinfo ({response.status_code}): {response.text}")
            return None
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching Google user info: {e}")
        return None

def verify_google_id_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Google ID token server-side via Google's tokeninfo service.
    """
    try:
        params = {"id_token": id_token}
        response = requests.get(GOOGLE_TOKENINFO_URL, params=params, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Google ID token verification failed ({response.status_code}): {response.text}")
            return None
        return response.json()
    except Exception as e:
        logger.error(f"Error verifying Google ID token: {e}")
        return None

def get_or_create_google_user(db: Session, google_info: Dict[str, Any]) -> Tuple[Optional[User], bool, str]:
    """
    Finds or creates a User from verified Google account profile.
    Handles:
    1. Existing Google User (login) -> Preserves user, business, permissions.
    2. Existing Local User with same email (safe account linking) -> Links google_id, preserves data.
    3. New User (provision user + business) -> Creates isolated business and user with standard defaults.

    Returns: (User, is_new: bool, action_taken: str)
    """
    google_id = str(google_info.get("sub") or google_info.get("id") or "").strip()
    email = str(google_info.get("email") or "").strip().lower()
    name = str(google_info.get("name") or google_info.get("given_name") or email.split("@")[0]).strip()
    picture = google_info.get("picture") or None
    email_verified = bool(google_info.get("email_verified") or google_info.get("verified_email", False))

    if not email:
        logger.error("Google user profile did not include an email address.")
        return None, False, "missing_email"

    # 1. Match by google_id
    if google_id:
        user_by_gid = db.query(User).filter(User.google_id == google_id).first()
        if user_by_gid:
            # Update latest profile picture and verified status if appropriate
            if picture and not user_by_gid.profile_picture:
                user_by_gid.profile_picture = picture
            user_by_gid.email_verified = True
            db.commit()
            db.refresh(user_by_gid)
            return user_by_gid, False, "login"

    # 2. Match by email (Safe Account Linking)
    user_by_email = db.query(User).filter(User.email == email).first()
    if user_by_email:
        logger.info(f"Linking Google account ({google_id}) to existing user '{user_by_email.name}' ({email}).")
        if google_id:
            user_by_email.google_id = google_id
        if picture and not user_by_email.profile_picture:
            user_by_email.profile_picture = picture
        user_by_email.email_verified = True
        db.commit()
        db.refresh(user_by_email)

        if user_by_email.business_id:
            log_activity(
                db,
                business_id=user_by_email.business_id,
                actor_type="Business Owner",
                action="Google Account Linked",
                description=f"User {user_by_email.name} linked Google OAuth sign-in to account ({email})."
            )

        return user_by_email, False, "linked"

    # 3. Create brand new User and isolated Business
    biz_name = f"{name}'s Business"
    biz = Business(
        name=biz_name,
        category="Small Business Services",
        currency="USD",
        timezone="America/New_York",
        payment_terms="Standard 30-day payment terms",
        email=email
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)

    new_user = User(
        name=name,
        email=email,
        password_hash=f"!oauth_google_{secrets.token_hex(16)}",  # Secure placeholder satisfying SQLite/Postgres schemas
        role="owner",
        business_id=biz.id,
        auth_provider="google",
        google_id=google_id or None,
        profile_picture=picture,
        email_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_activity(
        db,
        business_id=biz.id,
        actor_type="Business Owner",
        action="Google User Registered",
        description=f"New business owner registered via Google Sign-In: {name} ({email})."
    )

    return new_user, True, "created"

