"""
backend/app/auth.py
Campus Central API - Authentication & JWT Helpers

Phase 1 (June 18, 2026): Initial auth helpers (password hashing, JWT creation/verification).
Phase 2 (June 19, 2026): Added OTP login helper.
Phase 3 (June 25, 2026): Migrated from settings.SECRET_KEY to settings.JWT_SECRET.
                         JWT_SECRET now fetched from Azure Key Vault via config.
                         Azure SQL Database support (no code changes needed).
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .config import settings

# ============================================================
# SECURITY SCHEME
# ============================================================
security = HTTPBearer()
"""HTTP Bearer token security scheme for JWT authentication."""


# ============================================================
# PASSWORD HASHING (bcrypt - passlib‑free)
# ============================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash (passlib‑free).
    
    Args:
        plain_password: The plain text password to verify.
        hashed_password: The bcrypt hash to compare against.
        
    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    # Truncate to 72 bytes for compatibility with bcrypt
    plain_bytes = plain_password.encode('utf-8')[:72]
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash (passlib‑free).
    
    Args:
        password: The plain text password to hash.
        
    Returns:
        str: The bcrypt hash as a string.
    """
    # Truncate to 72 bytes as bcrypt ignores extra bytes
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


# ============================================================
# JWT TOKEN HELPERS
# ============================================================
def create_access_token(data: dict, expires_delta: Optional[timetime] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing the data to encode (e.g., {"sub": user_id}).
        expires_delta: Optional custom expiration time.
        
    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    # ✅ Convert sub to string if it's an int (Azure SQL expects string)
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # ✅ Use JWT_SECRET (fetched from Key Vault) instead of SECRET_KEY
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: The JWT token to decode.
        
    Returns:
        Optional[dict]: The decoded payload if valid, None otherwise.
    """
    try:
        # ✅ Use JWT_SECRET (fetched from Key Vault) instead of SECRET_KEY
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ============================================================
# DEPENDENCY: GET CURRENT USER
# ============================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the JWT token.
    
    Args:
        credentials: The HTTP Bearer token credentials.
        db: Database session.
        
    Returns:
        User: The authenticated user object.
        
    Raises:
        HTTPException: If the token is invalid or the user is not found.
    """
    token = credentials.credentials
    try:
        # ✅ Use JWT_SECRET (fetched from Key Vault) instead of SECRET_KEY
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user (alias for get_current_user).
    
    Args:
        current_user: The authenticated user from get_current_user.
        
    Returns:
        User: The current user.
    """
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current user and verify they have admin privileges.
    
    Args:
        current_user: The authenticated user from get_current_user.
        
    Returns:
        User: The current user if they are an admin.
        
    Raises:
        HTTPException: If the user is not an admin or principal.
    """
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# ============================================================
# OTP LOGIN HELPER
# ============================================================
def verify_otp_and_get_user(whatsapp: str, otp: str, db: Session) -> User:
    """
    Verify an OTP and return the associated user (creates user if new).
    
    Args:
        whatsapp: The WhatsApp number.
        otp: The OTP code to verify.
        db: Database session.
        
    Returns:
        User: The user associated with the WhatsApp number.
        
    Raises:
        HTTPException: If the OTP is invalid or expired.
    """
    from .models import OTPCode
    
    # Query the OTP record
    otp_record = db.query(OTPCode).filter(
        OTPCode.whatsapp == whatsapp,
        OTPCode.code == otp,
        OTPCode.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Find or create the user
    user = db.query(User).filter(User.whatsapp == whatsapp).first()
    if not user:
        user = User(
            whatsapp=whatsapp,
            full_name=whatsapp,  # Temporary name, user can update later
            password_hash="",    # No password for OTP-based users
            role="student",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Delete the used OTP record
    db.delete(otp_record)
    db.commit()
    
    return user


# ============================================================
# BACKWARD COMPATIBILITY (Phase 1 - Deprecated)
# ============================================================
# The following aliases are provided for backward compatibility
# with code that may still reference `settings.SECRET_KEY`.
# They will be removed in a future version.

# @deprecated: Use settings.JWT_SECRET instead
# SECRET_KEY = settings.JWT_SECRET  # Uncomment only if absolutely needed