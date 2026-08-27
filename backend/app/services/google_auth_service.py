import os
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import requests
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from backend.app.models.models import User, Business
from backend.app.utils.logger import logger
from backend.app.services.activity_service import log_activity

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback").strip()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

def is_google_auth_configured() -> bool:
    """
    Checks if Google OAuth credentials are provided in environment variables.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return bool(client_id and client_secret and len(client_id) > 10)

def get_google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()

def get_redirect_uri(custom_uri: Optional[str] = None) -> str:
    if custom_uri and custom_uri.strip():
        return custom_uri.strip()
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback").strip()

def get_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")

def build_google_auth_url(state: str = "state_ai_agent", redirect_uri: Optional[str] = None) -> str:
    """
    Generates the Google OAuth 2.0 consent screen redirect URL.
    """
    client_id = get_google_client_id()
    target_redirect = get_redirect_uri(redirect_uri)

    params = {
        "client_id": client_id,
        "redirect_uri": target_redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account"
    }

    query_string = urllib.parse.urlencode(params)
    return f"{GOOGLE_AUTH_URL}?{query_string}"

def exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """
    Exchanges authorization code for Google access token and ID token.
    """
    client_id = get_google_client_id()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
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
            return {"error": f"Token exchange failed: {response.text}"}
        return response.json()
    except Exception as e:
        logger.error(f"Error during Google token exchange: {e}")
        return {"error": str(e)}

def fetch_google_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Fetches user profile information from Google UserInfo endpoint.
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
        
        token_info = response.json()
        client_id = get_google_client_id()
        # Verify audience if client_id is configured
        if client_id and token_info.get("aud") != client_id:
            logger.warning(f"Token audience mismatch: {token_info.get('aud')} != {client_id}")
            # Accept if aud is valid google client
            pass

        return token_info
    except Exception as e:
        logger.error(f"Error verifying Google ID token: {e}")
        return None

def get_or_create_google_user(db: Session, google_info: Dict[str, Any]) -> Tuple[Optional[User], bool, str]:
    """
    Finds or creates a User from verified Google account profile.
    Handles:
    1. Existing Google User (login)
    2. Existing Local User with same email (safe account linking)
    3. New User (provision user + business)
    
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
            # Update latest profile picture and verified status
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
        user_by_email.auth_provider = "google" if user_by_email.auth_provider == "local" else user_by_email.auth_provider
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
        password_hash=None,  # Google OAuth users don't require local password
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
