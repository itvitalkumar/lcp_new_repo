"""
backend/routers/auth.py
Phase 1 version: Initial deployment (June 18, 2026) - all core auth endpoints.
Phase 2 update: Added TEST_MODE toggle for bypassing OTP during development/testing.
Docstrings added for all functions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import os

from app.database import get_db
from app.models import User
from app.schemas import UserSignup, UserLogin, TokenResponse, UserResponse, WhatsAppSignup, OTPVerify
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# OTP STORAGE (In-memory) - used only when TEST_MODE is False
otp_storage = {}

# Environment variable to enable test mode
# Set TEST_MODE=true in Azure App Settings or .env to bypass OTP for test phone numbers
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
# Comma-separated list of phone numbers that can bypass OTP in test mode
# Example: TEST_PHONE_NUMBERS=9876543210,9876543211
TEST_PHONE_NUMBERS = os.getenv("TEST_PHONE_NUMBERS", "").split(",") if os.getenv("TEST_PHONE_NUMBERS") else []

def generate_otp() -> str:
    """
    Generate a 6-digit OTP.
    Returns:
        str: A 6-digit OTP as a string.
    """
    return f"{random.randint(100000, 999999)}"


# ========== EMAIL-BASED SIGNUP ==========
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    User registration - creates a new user account using email and password.

    Args:
        user_data (UserSignup): User registration data.
        db (Session): Database session.

    Returns:
        TokenResponse: JWT access token and user details.

    Raises:
        HTTPException: If email is already registered.
    """
    
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        whatsapp=user_data.whatsapp,
        password_hash=hashed_password,
        role=user_data.role,
        hometown=user_data.hometown,
        district=user_data.district,
        college=user_data.college,
        gender=user_data.gender,
        hobbies=user_data.hobbies,
        course=user_data.course,
        specialization=user_data.specialization
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.id})
    
    user_response = UserResponse(
        id=new_user.id,
        email=new_user.email or "",
        full_name=new_user.full_name,
        role=new_user.role,
        created_at=new_user.created_at
    )
    
    return TokenResponse(access_token=access_token, user=user_response)


# ========== EMAIL-BASED LOGIN ==========
@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    User login with email and password - returns JWT token.

    Args:
        login_data (UserLogin): Email and password.
        db (Session): Database session.

    Returns:
        TokenResponse: JWT access token and user details.

    Raises:
        HTTPException: If email or password is invalid.
    """
    
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    
    user_response = UserResponse(
        id=user.id,
        email=user.email or "",
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at
    )
    
    return TokenResponse(access_token=access_token, user=user_response)


# ========== GET CURRENT USER ==========
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the profile of the currently authenticated user.

    Args:
        current_user (User): Authenticated user object.

    Returns:
        UserResponse: User profile data.
    """
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email or "",
        full_name=current_user.full_name,
        role=current_user.role,
        created_at=current_user.created_at
    )


# ========== CHECK IF USER EXISTS ==========
@router.get("/check-user")
async def check_user_exists(
    whatsapp: str,
    db: Session = Depends(get_db)
):
    """
    Check if a user with the given WhatsApp number already exists.

    Args:
        whatsapp (str): WhatsApp number to check.
        db (Session): Database session.

    Returns:
        dict: Contains 'exists' flag and user details if found.
    """
    user = db.query(User).filter(User.whatsapp == whatsapp).first()
    
    if user:
        return {
            "exists": True,
            "message": "User already exists with this WhatsApp number",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "whatsapp": user.whatsapp
            }
        }
    else:
        return {
            "exists": False,
            "message": "New user - can proceed with signup"
        }


# ========== WHATSAPP OTP ENDPOINTS ==========
@router.post("/send-otp")
async def send_otp(request: dict):
    """
    Send OTP to the provided WhatsApp number.
    In TEST_MODE, bypasses OTP for test phone numbers.

    Args:
        request (dict): Contains 'whatsapp' number.

    Returns:
        dict: Success message and debug OTP (if TEST_MODE is enabled).

    Raises:
        HTTPException: If the WhatsApp number is invalid.
    """
    whatsapp = request.get("whatsapp")
    if not whatsapp or len(whatsapp) != 10:
        raise HTTPException(status_code=400, detail="Invalid WhatsApp number")
    
    # If test mode is enabled and this is a test phone number, bypass OTP
    if TEST_MODE and whatsapp in TEST_PHONE_NUMBERS:
        print(f"🧪 TEST MODE: Bypassing OTP for {whatsapp}")
        return {"message": "OTP sent successfully (TEST MODE - bypassed)", "debug_otp": "000000"}
    
    otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=5)
    
    otp_storage[whatsapp] = {
        "otp": otp,
        "expires_at": expiry,
        "is_used": False
    }
    
    print(f"📱 OTP for {whatsapp}: {otp}")
    
    return {"message": "OTP sent successfully", "debug_otp": otp}


@router.post("/verify-otp")
async def verify_otp(request: dict, db: Session = Depends(get_db)):
    """
    Verify the OTP for a given WhatsApp number.
    In TEST_MODE, bypasses verification for test phone numbers.

    Args:
        request (dict): Contains 'whatsapp' and 'otp'.
        db (Session): Database session.

    Returns:
        dict: Verification status, user existence, and token if user exists.

    Raises:
        HTTPException: If OTP is invalid, expired, or already used.
    """
    whatsapp = request.get("whatsapp")
    otp = request.get("otp")
    
    # If test mode is enabled and this is a test phone number, bypass verification
    if TEST_MODE and whatsapp in TEST_PHONE_NUMBERS:
        print(f"🧪 TEST MODE: Bypassing OTP verification for {whatsapp}")
        user = db.query(User).filter(User.whatsapp == whatsapp).first()
        if user:
            access_token = create_access_token(data={"sub": user.id})
            return {
                "verified": True,
                "exists": True,
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "whatsapp": user.whatsapp,
                    "full_name": user.full_name,
                    "course": user.course
                }
            }
        else:
            return {"verified": True, "exists": False}
    
    stored = otp_storage.get(whatsapp)
    
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP requested")
    
    if stored["is_used"]:
        raise HTTPException(status_code=400, detail="OTP already used")
    
    if datetime.now() > stored["expires_at"]:
        raise HTTPException(status_code=400, detail="OTP expired")
    
    if stored["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    stored["is_used"] = True
    
    user = db.query(User).filter(User.whatsapp == whatsapp).first()
    
    if user:
        access_token = create_access_token(data={"sub": user.id})
        return {
            "verified": True,
            "exists": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "whatsapp": user.whatsapp,
                "full_name": user.full_name,
                "course": user.course
            }
        }
    else:
        return {"verified": True, "exists": False}


# ========== OTP-ONLY LOGIN (NO AUTO-CREATE) ==========
@router.post("/otp-login", response_model=TokenResponse)
async def otp_login(data: OTPVerify, db: Session = Depends(get_db)):
    """
    Verify OTP and return JWT token for EXISTING users only.
    New users must sign up via /whatsapp-signup (which collects name).

    Args:
        data (OTPVerify): Contains 'whatsapp' and 'otp'.
        db (Session): Database session.

    Returns:
        TokenResponse: JWT access token and user details.

    Raises:
        HTTPException: If OTP is invalid, expired, or user not found.
    """
    whatsapp = data.whatsapp
    otp = data.otp

    # If test mode is enabled and this is a test phone number, bypass verification
    if TEST_MODE and whatsapp in TEST_PHONE_NUMBERS:
        print(f"🧪 TEST MODE: Bypassing OTP verification for {whatsapp}")
        user = db.query(User).filter(User.whatsapp == whatsapp).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Please sign up first."
            )
        access_token = create_access_token(data={"sub": user.id})
        user_response = UserResponse(
            id=user.id,
            email=user.email or "",
            full_name=user.full_name,
            role=user.role,
            created_at=user.created_at
        )
        return TokenResponse(access_token=access_token, user=user_response)

    # Regular OTP verification
    stored = otp_storage.get(whatsapp)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP requested")
    if stored["is_used"]:
        raise HTTPException(status_code=400, detail="OTP already used")
    if datetime.now() > stored["expires_at"]:
        raise HTTPException(status_code=400, detail="OTP expired")
    if stored["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    stored["is_used"] = True

    user = db.query(User).filter(User.whatsapp == whatsapp).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please sign up first."
        )

    access_token = create_access_token(data={"sub": user.id})
    user_response = UserResponse(
        id=user.id,
        email=user.email or "",
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at
    )
    return TokenResponse(access_token=access_token, user=user_response)


# ========== WHATSAPP-BASED SIGNUP ==========
@router.post("/whatsapp-signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def whatsapp_signup(user_data: dict, db: Session = Depends(get_db)):
    """
    Signup using WhatsApp number + password (and optional photo).
    Password is hashed and stored.

    Args:
        user_data (dict): Contains 'whatsapp', 'full_name', 'course', 'photo', 'password'.
        db (Session): Database session.

    Returns:
        TokenResponse: JWT access token and user details.

    Raises:
        HTTPException: If required fields are missing or WhatsApp number already registered.
    """
    whatsapp = user_data.get("whatsapp")
    full_name = user_data.get("full_name")
    course = user_data.get("course")
    photo = user_data.get("photo")
    password = user_data.get("password")

    if not whatsapp or not full_name:
        raise HTTPException(status_code=400, detail="Missing required fields")

    existing_user = db.query(User).filter(User.whatsapp == whatsapp).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="WhatsApp number already registered")

    hashed_password = get_password_hash(password) if password else ""

    new_user = User(
        whatsapp=whatsapp,
        full_name=full_name,
        course=course or "",
        password_hash=hashed_password,
        photo=photo,
        role="student"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.id})
    user_response = UserResponse(
        id=new_user.id,
        email=new_user.email or "",
        full_name=new_user.full_name,
        role=new_user.role,
        created_at=new_user.created_at
    )
    return TokenResponse(access_token=access_token, user=user_response)


# ========== WHATSAPP-BASED LOGIN ==========
@router.post("/whatsapp-login", response_model=TokenResponse)
def whatsapp_login(login_data: dict, db: Session = Depends(get_db)):
    """
    Login using WhatsApp number + password.

    Args:
        login_data (dict): Contains 'whatsapp' and 'password'.
        db (Session): Database session.

    Returns:
        TokenResponse: JWT access token and user details.

    Raises:
        HTTPException: If WhatsApp number or password is invalid.
    """
    whatsapp = login_data.get("whatsapp")
    password = login_data.get("password")
    
    user = db.query(User).filter(User.whatsapp == whatsapp).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WhatsApp number or password"
        )
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WhatsApp number or password"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    
    user_response = UserResponse(
        id=user.id,
        email=user.email or "",
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at
    )
    
    return TokenResponse(access_token=access_token, user=user_response)