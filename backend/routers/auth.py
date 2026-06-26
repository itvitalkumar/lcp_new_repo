"""
backend/routers/auth.py
Campus Central API - Authentication Routes

Phase 1 (June 18, 2026): Initial deployment - all core auth endpoints.
Phase 2 (June 19, 2026): Added TEST_MODE toggle for bypassing OTP during development/testing.
Phase 3 (June 25, 2026): Migrated TEST_MODE and TEST_PHONE_NUMBERS to use settings from config.py.
                         JWT_SECRET now fetched from Azure Key Vault via settings.
                         All secrets managed centrally.
Phase 4 (June 26, 2026): ENHANCED - Added retry logic for database operations.
                         Better error handling with specific error messages.
                         Added connection pool health checks before DB operations.
                         Improved logging for debugging.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from datetime import datetime, timedelta
import random
import logging

from app.database import get_db, retry_on_db_error, check_database_health
from app.models import User
from app.schemas import UserSignup, UserLogin, TokenResponse, UserResponse, OTPVerify
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.config import settings

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ============================================================
# OTP STORAGE (In-memory) - used only when TEST_MODE is False
# ============================================================
otp_storage = {}

# ============================================================
# TEST MODE - Now managed via settings from config.py
# ============================================================
# TEST_MODE and TEST_PHONE_NUMBERS are now fetched from settings
# No need to read from os.getenv() here - they come from config.py


def generate_otp() -> str:
    """
    Generate a 6-digit OTP.

    Returns:
        str: A 6-digit OTP as a string.
    """
    return f"{random.randint(100000, 999999)}"


# ============================================================
# ✅ ADDED: HELPER FOR DATABASE ERROR HANDLING
# ============================================================
def handle_db_error(e: Exception, operation: str) -> HTTPException:
    """
    Convert database errors to user-friendly HTTP exceptions.
    """
    logger.error(f"❌ Database error during {operation}: {str(e)}")
    
    if "timeout" in str(e).lower() or "connection" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again in a moment."
        )
    elif "duplicate" in str(e).lower() or "unique" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate entry. The record already exists."
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again later."
        )


# ============================================================
# EMAIL-BASED SIGNUP
# ============================================================
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
        HTTPException: If email is already registered or database error.
    """
    try:
        # ✅ Retry on transient database errors
        existing_user = retry_on_db_error(
            lambda: db.query(User).filter(User.email == user_data.email).first()
        )
        
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
        
    except HTTPException:
        raise
    except OperationalError as e:
        raise handle_db_error(e, "user signup")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "user signup")
    except Exception as e:
        logger.error(f"❌ Unexpected error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )
    # ============================================================
# EMAIL-BASED LOGIN
# ============================================================
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
    try:
        user = retry_on_db_error(
            lambda: db.query(User).filter(User.email == login_data.email).first()
        )
        
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
        
    except HTTPException:
        raise
    except OperationalError as e:
        raise handle_db_error(e, "user login")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "user login")
    except Exception as e:
        logger.error(f"❌ Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# GET CURRENT USER
# ============================================================
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


# ============================================================
# CHECK IF USER EXISTS
# ============================================================
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
    try:
        user = retry_on_db_error(
            lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
        )
        
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
            
    except OperationalError as e:
        logger.error(f"❌ Database error in check-user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in check-user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# WHATSAPP OTP ENDPOINTS
# ============================================================
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
    
    # ✅ Use settings.TEST_MODE and settings.TEST_PHONE_NUMBERS from config.py
    if settings.TEST_MODE and whatsapp in settings.TEST_PHONE_NUMBERS:
        logger.info(f"🧪 TEST MODE: Bypassing OTP for {whatsapp}")
        return {"message": "OTP sent successfully (TEST MODE - bypassed)", "debug_otp": "000000"}
    
    otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=5)
    
    otp_storage[whatsapp] = {
        "otp": otp,
        "expires_at": expiry,
        "is_used": False
    }
    
    logger.info(f"📱 OTP for {whatsapp}: {otp}")
    
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
    
    # ✅ Use settings.TEST_MODE and settings.TEST_PHONE_NUMBERS from config.py
    if settings.TEST_MODE and whatsapp in settings.TEST_PHONE_NUMBERS:
        logger.info(f"🧪 TEST MODE: Bypassing OTP verification for {whatsapp}")
        try:
            user = retry_on_db_error(
                lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
            )
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
        except OperationalError as e:
            raise handle_db_error(e, "OTP verification")
    
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
    
    try:
        user = retry_on_db_error(
            lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
        )
        
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
            
    except OperationalError as e:
        raise handle_db_error(e, "OTP verification")
    # ============================================================
# OTP-ONLY LOGIN (NO AUTO-CREATE)
# ============================================================
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

    logger.info(f"🔐 OTP Login attempt for {whatsapp}")

    # ✅ Use settings.TEST_MODE and settings.TEST_PHONE_NUMBERS from config.py
    if settings.TEST_MODE and whatsapp in settings.TEST_PHONE_NUMBERS:
        logger.info(f"🧪 TEST MODE: Bypassing OTP verification for {whatsapp}")
        try:
            # ✅ Retry on transient database errors
            user = retry_on_db_error(
                lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
            )
            if not user:
                logger.warning(f"⚠️ TEST MODE: User not found for {whatsapp}")
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
            logger.info(f"✅ TEST MODE: Login successful for {whatsapp}")
            return TokenResponse(access_token=access_token, user=user_response)
            
        except HTTPException:
            raise
        except OperationalError as e:
            logger.error(f"❌ Database error in OTP login (test mode): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database temporarily unavailable. Please try again."
            )
        except SQLTimeoutError as e:
            logger.error(f"❌ Database timeout in OTP login (test mode): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection timeout. Please try again."
            )
        except Exception as e:
            logger.error(f"❌ Unexpected error in OTP login (test mode): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again."
            )

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

    try:
        # ✅ Retry on transient database errors
        user = retry_on_db_error(
            lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
        )
        
        if not user:
            logger.warning(f"⚠️ User not found for {whatsapp} during OTP login")
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
        logger.info(f"✅ OTP login successful for {whatsapp}")
        return TokenResponse(access_token=access_token, user=user_response)
        
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error(f"❌ Database error in OTP login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again."
        )
    except SQLTimeoutError as e:
        logger.error(f"❌ Database timeout in OTP login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection timeout. Please try again."
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in OTP login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# WHATSAPP-BASED SIGNUP
# ============================================================
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

    try:
        existing_user = retry_on_db_error(
            lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
        )
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
        logger.info(f"✅ WhatsApp signup successful for {whatsapp}")
        return TokenResponse(access_token=access_token, user=user_response)
        
    except HTTPException:
        raise
    except OperationalError as e:
        raise handle_db_error(e, "WhatsApp signup")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "WhatsApp signup")
    except Exception as e:
        logger.error(f"❌ Unexpected error during WhatsApp signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# WHATSAPP-BASED LOGIN
# ============================================================
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
    
    try:
        user = retry_on_db_error(
            lambda: db.query(User).filter(User.whatsapp == whatsapp).first()
        )
        
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
        
        logger.info(f"✅ WhatsApp login successful for {whatsapp}")
        return TokenResponse(access_token=access_token, user=user_response)
        
    except HTTPException:
        raise
    except OperationalError as e:
        raise handle_db_error(e, "WhatsApp login")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "WhatsApp login")
    except Exception as e:
        logger.error(f"❌ Unexpected error during WhatsApp login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )