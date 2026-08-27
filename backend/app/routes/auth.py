import urllib.parse
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import User, Business
from backend.app.schemas.schemas import (
    UserLogin, UserRegister, Token, UserOut, UserForgotPassword,
    GoogleTokenVerifyRequest
)
from backend.app.auth.security import verify_password, get_password_hash
from backend.app.auth.jwt import create_access_token
from backend.app.auth.deps import get_current_user
from backend.app.services.activity_service import log_activity
from backend.app.services.email_delivery import send_real_email
from backend.app.services.google_auth_service import (
    is_google_auth_configured, get_google_client_id, build_google_auth_url,
    exchange_code_for_tokens, fetch_google_user_info, verify_google_id_token,
    get_or_create_google_user, get_frontend_url
)
from backend.app.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Create or associate business
    biz = Business(
        name=user_in.business_name or "My Business",
        currency=user_in.currency or "USD",
        category="Small Business Services",
        email=user_in.email.lower()
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)

    new_user = User(
        name=user_in.name,
        email=user_in.email.lower(),
        password_hash=get_password_hash(user_in.password),
        role="owner",
        business_id=biz.id,
        auth_provider="local",
        email_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id), "email": new_user.email})

    log_activity(
        db,
        business_id=biz.id,
        actor_type="Business Owner",
        action="User Registered",
        description=f"New business owner account created for {new_user.name} ({new_user.email})."
    )

    new_user.business_name = biz.name
    return {"access_token": token, "token_type": "bearer", "user": new_user}


@router.post("/login", response_model=Token)
def login_user(login_in: UserLogin, db: Session = Depends(get_db)):
    email_clean = str(login_in.email).strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    
    # If the user doesn't exist yet, auto-provision their account and business dynamically
    if not user:
        raw_name = email_clean.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ').title()
        user_name = raw_name if raw_name else "Business Owner"
        biz_name = f"{user_name}'s Business"

        biz = Business(
            name=biz_name,
            category="Small Business Services",
            currency="USD",
            timezone="America/New_York",
            payment_terms="Standard 30-day payment terms",
            email=email_clean
        )
        db.add(biz)
        db.commit()
        db.refresh(biz)

        user = User(
            name=user_name,
            email=email_clean,
            password_hash=get_password_hash(login_in.password),
            role="owner",
            business_id=biz.id,
            auth_provider="local",
            email_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        log_activity(
            db,
            business_id=biz.id,
            actor_type="Business Owner",
            action="Account Initialized",
            description=f"New business owner account created for {user.name} ({user.email})."
        )
    else:
        if user.password_hash:
            if not verify_password(login_in.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password for this account. Please re-enter your password or click '1-Click Demo Login'."
                )
        else:
            # User previously signed in via Google OAuth only
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account was registered with Google Sign-In. Please click 'Continue with Google' to log in."
            )

    token = create_access_token(data={"sub": str(user.id), "email": user.email})

    if user.business_id:
        log_activity(
            db,
            business_id=user.business_id,
            actor_type="Business Owner",
            action="User Logged In",
            description=f"User {user.name} logged into the system."
        )

    user.business_name = user.business.name if user.business else "My Business"
    return {"access_token": token, "token_type": "bearer", "user": user}


# ----------------- GOOGLE OAUTH 2.0 ROUTES -----------------

@router.get("/google/config")
def get_google_auth_config():
    """
    Returns public Google OAuth configuration for frontend initialization.
    """
    return {
        "configured": is_google_auth_configured(),
        "client_id": get_google_client_id()
    }


@router.get("/google/login")
def google_oauth_login(
    redirect_uri: Optional[str] = Query(None),
    state: Optional[str] = Query("state_ai_agent")
):
    """
    Redirects user's browser to the Google OAuth 2.0 consent screen.
    """
    if not is_google_auth_configured():
        auth_url = build_google_auth_url(state=state or "state_ai_agent", redirect_uri=redirect_uri)
        return {
            "status": "warning",
            "configured": False,
            "auth_url": auth_url,
            "message": "Google OAuth credentials (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET) are not set in environment."
        }

    auth_url = build_google_auth_url(state=state or "state_ai_agent", redirect_uri=redirect_uri)
    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback")
def google_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handles Google OAuth redirect, exchanges code for user profile,
    creates or links user, and redirects to frontend with application JWT.
    """
    frontend_base = get_frontend_url()

    if error:
        logger.warning(f"Google OAuth cancelled or returned error: {error}")
        error_msg = urllib.parse.quote("Google sign-in was cancelled.")
        return RedirectResponse(url=f"{frontend_base}/?error=google_cancelled&message={error_msg}")

    if not code:
        error_msg = urllib.parse.quote("Missing authorization code from Google.")
        return RedirectResponse(url=f"{frontend_base}/?error=oauth_failed&message={error_msg}")

    # Exchange authorization code with Google token endpoint
    token_response = exchange_code_for_tokens(code)
    if "error" in token_response or not token_response.get("access_token"):
        err_detail = token_response.get("error", "Failed to exchange token with Google.")
        logger.error(f"Google code exchange failed: {err_detail}")
        error_msg = urllib.parse.quote("Unable to sign in with Google. Please try again.")
        return RedirectResponse(url=f"{frontend_base}/?error=exchange_failed&message={error_msg}")

    access_token = token_response["access_token"]
    user_info = fetch_google_user_info(access_token)
    if not user_info:
        error_msg = urllib.parse.quote("Could not retrieve Google profile details.")
        return RedirectResponse(url=f"{frontend_base}/?error=profile_failed&message={error_msg}")

    user, is_new, action_taken = get_or_create_google_user(db, user_info)
    if not user:
        error_msg = urllib.parse.quote("Could not provision user account from Google profile.")
        return RedirectResponse(url=f"{frontend_base}/?error=user_creation_failed&message={error_msg}")

    # Issue application JWT token
    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    action_label = "created" if is_new else ("linked" if action_taken == "linked" else "login")
    return RedirectResponse(
        url=f"{frontend_base}/?token={jwt_token}&provider=google&action={action_label}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@router.post("/google/verify", response_model=Token)
def verify_google_credential(
    payload: GoogleTokenVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Direct verification endpoint for Google Identity Services / OneTap / Popup tokens.
    """
    user_info = None

    if payload.credential:
        # ID Token verification
        user_info = verify_google_id_token(payload.credential)

    elif payload.code:
        # Code exchange
        token_response = exchange_code_for_tokens(payload.code, payload.redirect_uri)
        if token_response.get("access_token"):
            user_info = fetch_google_user_info(token_response["access_token"])

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to verify Google authentication credentials. Please try again."
        )

    user, is_new, action_taken = get_or_create_google_user(db, user_info)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize account from Google identity."
        )

    jwt_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    user.business_name = user.business.name if user.business else "My Business"

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/forgot-password")
def forgot_password(payload: UserForgotPassword, db: Session = Depends(get_db)):
    email_clean = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address. Please verify your email or register a new business."
        )
    
    if payload.new_password:
        if len(payload.new_password) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 4 characters long."
            )
        user.password_hash = get_password_hash(payload.new_password)
        db.commit()
        db.refresh(user)
        
        if user.business_id:
            log_activity(
                db,
                business_id=user.business_id,
                actor_type="Business Owner",
                action="Password Reset",
                description=f"Password was successfully reset for {user.name} ({user.email})."
            )
        
        send_real_email(
            to_email=user.email,
            subject="Password Reset Confirmation - AI Business Agent",
            body=f"Hello {user.name},\n\nYour account password has been successfully reset. You can now sign in with your new credentials.\n\nBest regards,\nAI Business Agent Team"
        )
        return {
            "status": "success",
            "message": "Password reset successfully! You can now sign in with your new password."
        }
    else:
        send_real_email(
            to_email=user.email,
            subject="Password Reset Instructions - AI Business Agent",
            body=f"Hello {user.name},\n\nA password reset was requested for your account ({user.email}). Please use the recovery form on the login screen to set a new password.\n\nBest regards,\nAI Business Agent Team"
        )
        return {
            "status": "success",
            "message": f"Password reset instructions have been dispatched to {user.email}."
        }


@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    if current_user.business:
        current_user.business_name = current_user.business.name
    return current_user


users_router = APIRouter(prefix="/api/users", tags=["Users"])

@users_router.get("/me", response_model=UserOut)
def get_current_user_profile_alias(current_user: User = Depends(get_current_user)):
    if current_user.business:
        current_user.business_name = current_user.business.name
    return current_user
