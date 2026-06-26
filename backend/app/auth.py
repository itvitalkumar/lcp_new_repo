"""
backend/app/auth.py
Campus Central API - Authentication & JWT Helpers

Phase 1 (June 18, 2026): Initial auth helpers (password hashing, JWT creation/verification).
Phase 2 (June 19, 2026): Added OTP login helper.
Phase 3 (June 25, 2026): Migrated from settings.SECRET_KEY to settings.JWT_SECRET.
                         JWT_SECRET now fetched from Azure Key Vault via config.
                         Azure SQL Database support (no code changes needed).
Phase 4 (June 26, 2026): ENHANCED - Added caching for JWT_SECRET to reduce Key Vault calls.
                         Better error handling for token validation.
                         Added retry logic for transient database errors.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import time
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db, retry_on_db_error
from .models import User
from .config import settings

# ============================================================
# SECURITY SCHEME
# ============================================================
security = HTTPBearer()
"""HTTP Bearer token security scheme for JWT authentication."""

# ============================================================
# ✅ ADDED: JWT_SECRET CACHE
# ============================================================
_jwt_secret_cache = None
_jwt_secret_timestamp = None
_JWT_CACHE_DURATION = 3600  # 1 hour in seconds


def get_jwt_secret() -> str:
    """
    Get JWT_SECRET with caching to reduce Key Vault calls.
    Refreshes cache after 1 hour or on failure.
    """
    global _jwt_secret_cache, _jwt_secret_timestamp
    
    current_time = time.time()
    
    # Check if cache is valid
    if (_jwt_secret_cache is not None and 
        _jwt_secret_timestamp is not None and 
        (current_time - _jwt_secret_timestamp) < _JWT_CACHE_DURATION):
        return _jwt_secret_cache
    
    # Refresh cache
    try:
        secret = settings.JWT_SECRET
        if not secret:
            raise ValueError("JWT_SECRET not configured in settings")
        _jwt_secret_cache = secret
        _jwt_secret_timestamp = current_time
        print("✅ JWT_SECRET cache refreshed")
        return secret
    except Exception as e:
        # If cache exists, use it even if expired
        if _jwt_secret_cache:
            print(f"⚠️ Failed to refresh JWT_SECRET, using cached value: {e}")
            return _jwt_secret_cache
        raise


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
def create_access_token(data: dict, expires_delta: Optional[datetime] = None) -> str:
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
    
    # ✅ Use cached JWT_SECRET
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: The JWT token to decode.
        
    Returns:
        Optional[dict]: The decoded payload if valid, None otherwise.
    """
    try:
        # ✅ Use cached JWT_SECRET
        return jwt.decode(token, get_jwt_secret(), algorithms=[settings.ALGORITHM])
    except JWTError as e:
        print(f"⚠️ JWT decode error: {e}")
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
        # ✅ Use cached JWT_SECRET
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        user_id = int(user_id_str)
    except JWTError as e:
        print(f"⚠️ JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    # ✅ Retry on transient database errors
    try:
        user = retry_on_db_error(lambda: db.query(User).filter(User.id == user_id).first())
    except Exception as e:
        print(f"❌ Database error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again."
        )
    
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
    
    # ✅ Retry on transient database errors
    try:
        otp_record = retry_on_db_error(lambda: db.query(OTPCode).filter(
            OTPCode.whatsapp == whatsapp,
            OTPCode.code == otp,
            OTPCode.expires_at > datetime.utcnow()
        ).first())
    except Exception as e:
        print(f"❌ Database error in verify_otp: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again."
        )
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Find or create the user
    try:
        user = retry_on_db_error(lambda: db.query(User).filter(User.whatsapp == whatsapp).first())
    except Exception as e:
        print(f"❌ Database error finding user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again."
        )
    
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
# ✅ ADDED: FORCE REFRESH JWT SECRET
# ============================================================
def refresh_jwt_secret():
    """
    Force refresh the JWT_SECRET cache.
    Useful when Key Vault secret is rotated.
    """
    global _jwt_secret_cache, _jwt_secret_timestamp
    _jwt_secret_cache = None
    _jwt_secret_timestamp = None
    return get_jwt_secret()


# ============================================================
# BACKWARD COMPATIBILITY (Phase 1 - Deprecated)
# ============================================================
# The following aliases are provided for backward compatibility
# with code that may still reference `settings.SECRET_KEY`.
# They will be removed in a future version.

# @deprecated: Use settings.JWT_SECRET instead
# SECRET_KEY = settings.JWT_SECRET  # Uncomment only if absolutely needed