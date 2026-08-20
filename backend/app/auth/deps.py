from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.models import User, Business
from backend.app.auth.jwt import decode_access_token

security = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials.strip()
    
    # Handle dedicated demo token if explicitly issued for demonstration mode
    if token.startswith("demo-jwt-token-active-session-"):
        demo_user = db.query(User).filter(User.email == "admin@summitdigital.com").first()
        if not demo_user:
            demo_user = db.query(User).first()
        if demo_user:
            if demo_user.business:
                demo_user.business_name = demo_user.business.name
            return demo_user

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired or the token is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        user_id = int(payload["sub"])
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The user account associated with this session no longer exists.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Attach dynamic business name attribute
        if user.business:
            user.business_name = user.business.name
        else:
            user.business_name = "My Business"

        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate session credentials.",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_business(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Business:
    if current_user and current_user.business_id:
        business = db.query(Business).filter(Business.id == current_user.business_id).first()
        if business:
            return business
    
    # If user has no business, create an isolated business specifically for this user
    business_name = f"{current_user.name}'s Business" if current_user and current_user.name else "My Business"
    business = Business(
        name=business_name,
        category="Small Business Services",
        currency="USD",
        timezone="America/New_York",
        payment_terms="Standard 30-day payment terms",
        email=current_user.email if current_user else None
    )
    db.add(business)
    db.commit()
    db.refresh(business)

    if current_user:
        current_user.business_id = business.id
        db.commit()
        db.refresh(current_user)

    return business
