"""
backend/app/config.py
Phase 1 version: Initial deployment (June 18, 2026) - core app settings.
Phase 2 update: Added TEST_MODE and TEST_PHONE_NUMBERS for OTP bypass during development/testing.
Docstrings added for all settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Application settings loaded from environment variables.
    All settings can be overridden by setting environment variables.
    """
    
    # ========== APP SETTINGS ==========
    APP_NAME: str = "Campus Central API"
    """Name of the application."""
    
    APP_VERSION: str = "1.0.0"
    """Version of the application."""
    
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    """Enable debug mode. Set to 'false' in production."""
    
    # ========== DATABASE ==========
    #DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./campus_central.db")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////home/site/wwwroot/campus_central.db")
    """Database connection URL. Supports SQLite, PostgreSQL, etc."""
    
    # ========== SECURITY ==========
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    """Secret key for JWT token signing. Must be changed in production."""
    
    ALGORITHM: str = "HS256"
    """JWT signing algorithm."""
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days
    """JWT token expiration time in minutes."""
    
    # ========== FILE UPLOAD ==========
    UPLOAD_DIR: str = "uploads"
    """Directory where uploaded files are stored."""
    
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    """Maximum allowed file upload size in bytes."""
    
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    """Allowed file extensions for upload."""
    
    # ========== CORS ==========
    ALLOWED_ORIGINS: list = [
        "http://localhost:5500",      # VS Code Live Server
        "http://localhost:3000",      # React dev
        "http://localhost:8080",      # Alternative
        "exp://localhost:8081",       # React Native Expo
        "https://wonderful-flower-0739f5710.7.azurestaticapps.net",  # Your live frontend
        "https://agreeable-pond-0372cb110.7.azurestaticapps.net",    # New frontend URL
        "https://mycampuscentral.in",                                 # Custom domain
        "https://www.mycampuscentral.in",                             # Custom domain with www
    ]
    """List of allowed origins for CORS. Add your frontend URLs here."""
    
    # ========== LUCKY NUMBER GAME ==========
    TEACHER_MIN_POINTS: int = 18
    """Minimum points for teacher lucky number game."""
    
    TEACHER_MAX_POINTS: int = 81
    """Maximum points for teacher lucky number game."""
    
    CELEBRATION_MIN_POINTS: int = 39
    """Minimum points for celebration lucky number game."""
    
    CELEBRATION_MAX_POINTS: int = 93
    """Maximum points for celebration lucky number game."""
    
    # Point thresholds for labels
    ULTRA_LUCKY_MAX: int = 40
    """Points below this threshold are considered 'Ultra Lucky'."""
    
    LUCKIER_MAX: int = 60
    """Points below this threshold (and above ULTRA_LUCKY_MAX) are 'Luckier'."""
    # Above 60 = LUCKY
    
    # ========== RAZORPAY PAYMENT SETTINGS ==========
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_T0KRH1p12BN6S3")
    """Razorpay API Key ID for payment processing."""
    
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "13NK59ubLhjQAp75VzkLm803")
    """Razorpay API Key Secret for payment processing."""
    
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "your_webhook_secret_here")
    """Razorpay webhook secret for verifying webhook signatures."""
    
    # ========== TEST MODE (Phase 2 - Added June 19, 2026) ==========
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"
    """
    Enable test mode to bypass OTP verification for development/testing.
    Set to 'true' to enable. When enabled, phone numbers listed in TEST_PHONE_NUMBERS
    will bypass OTP verification.
    """
    
    TEST_PHONE_NUMBERS: list = os.getenv("TEST_PHONE_NUMBERS", "").split(",") if os.getenv("TEST_PHONE_NUMBERS") else []
    """
    Comma-separated list of phone numbers that can bypass OTP in test mode.
    Example: "9686449386,9876543210"
    Only effective when TEST_MODE is True.
    """


settings = Settings()