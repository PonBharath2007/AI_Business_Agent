from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import User, Business
from backend.app.schemas.schemas import UserLogin, UserRegister, Token, UserOut, UserForgotPassword
from backend.app.auth.security import verify_password, get_password_hash
from backend.app.auth.jwt import create_access_token
from backend.app.auth.deps import get_current_user
from backend.app.services.activity_service import log_activity
from backend.app.services.email_delivery import send_real_email

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
        business_id=biz.id
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
            business_id=biz.id
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
        if not verify_password(login_in.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this account. Please re-enter your password or click '1-Click Demo Login'."
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

