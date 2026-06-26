"""
backend/app/config.py

Campus Central - Configuration

Phase 1 (June 18, 2026): Core app settings.
Phase 2 (June 19, 2026): Added TEST_MODE and TEST_PHONE_NUMBERS for OTP bypass.
Phase 3 (June 25, 2026): Integrated Azure Key Vault for secure secret management.
Phase 4 (June 26, 2026): REFACTORED - Production-ready config.
                         - Added logging instead of print()
                         - Lazy secret loading for faster startup
                         - Added USE_SQLITE switch
                         - ODBC Driver 18 (current Azure standard)
                         - Azure CLI support for local development
                         - Removed DATABASE_URL (now built in database.py)
                         - Key Vault URL must be set via environment variable
                         - Added type hints for better code quality
                         - Removed hardcoded Razorpay test keys
                         - Added warnings for missing Razorpay keys
"""

import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Load environment variables from .env file (for local development)
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)


class Settings:
    """
    Application settings loaded from environment variables and Azure Key Vault.
    Secrets are loaded lazily to improve startup performance.
    """
    
    # ========== APP SETTINGS ==========
    APP_NAME: str = "Campus Central API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ========== KEY VAULT CONFIGURATION ==========
    # ✅ Must be set via Application Setting in Azure App Service
    # ✅ Or .env file for local development
    KEY_VAULT_URL: str = os.getenv("AZURE_KEY_VAULT_URL", "")
    
    _secret_client: Optional[SecretClient] = None
    _secret_cache: Dict[str, str] = {}
    
    @classmethod
    def _get_secret_client(cls):
        """Lazy-initialize Key Vault client with optimized credentials."""
        if cls._secret_client is None:
            # ✅ Validate Key Vault URL is configured
            if not cls.KEY_VAULT_URL:
                logger.warning("AZURE_KEY_VAULT_URL is not configured. Secrets will not be available.")
                return None
            
            try:
                # ✅ Balanced DefaultAzureCredential:
                # - Works on Azure App Service (Managed Identity)
                # - Works locally with az login
                # - Skips only VS Code and Shared Token Cache for speed
                credential = DefaultAzureCredential(
                    exclude_visual_studio_code_credential=True,
                    exclude_shared_token_cache_credential=True,
                )
                cls._secret_client = SecretClient(
                    vault_url=cls.KEY_VAULT_URL, 
                    credential=credential
                )
                logger.info("✅ Key Vault client initialized successfully")
            except Exception as e:
                logger.warning("Failed to initialize Key Vault client: %s", e)
                cls._secret_client = None
        return cls._secret_client
    
    @classmethod
    def _get_secret(cls, secret_name: str, fallback: Optional[str] = None) -> str:
        """
        Fetch a secret from Azure Key Vault with caching.
        Returns fallback value if secret cannot be fetched.
        """
        # ✅ Check cache first
        if secret_name in cls._secret_cache:
            return cls._secret_cache[secret_name]
        
        # ✅ Try Key Vault
        client = cls._get_secret_client()
        if client:
            try:
                value = client.get_secret(secret_name).value
                cls._secret_cache[secret_name] = value
                logger.debug("Secret '%s' fetched from Key Vault", secret_name)
                return value
            except Exception as e:
                logger.warning("Failed to fetch secret '%s': %s", secret_name, e)
        
        # ✅ Fallback to environment variable
        env_value = os.getenv(secret_name)
        if env_value:
            cls._secret_cache[secret_name] = env_value
            logger.debug("Secret '%s' fetched from environment", secret_name)
            return env_value
        
        # ✅ Use fallback
        if fallback is not None:
            cls._secret_cache[secret_name] = fallback
            logger.debug("Secret '%s' using fallback value", secret_name)
            return fallback
        
        logger.warning("No value found for secret '%s'", secret_name)
        return ""
    
    # ========== DATABASE (Azure SQL) ==========
    # ✅ Managed Identity ONLY - no username/password needed
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "false").lower() == "true"
    
    DB_HOST: str = os.getenv("DB_HOST", "campuscentral-sql-server.database.windows.net")
    DB_NAME: str = os.getenv("DB_NAME", "campuscentral_sql_db")
    # ✅ ODBC Driver 18 - Current Azure App Service standard
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    
    # SQLite (for local development)
    SQLITE_DATABASE_URL: str = os.getenv(
        "SQLITE_DATABASE_URL",
        "sqlite:///./campus_central.db"
    )
    
    # ========== SECURITY ==========
    # ✅ Lazy-loaded from Key Vault
    _jwt_secret: Optional[str] = None
    
    @property
    def JWT_SECRET(self) -> str:
        """Lazy-load JWT_SECRET from Key Vault."""
        if self._jwt_secret is None:
            self._jwt_secret = self._get_secret(
                "JWT-Secret",
                fallback=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
            )
            if self._jwt_secret == "your-super-secret-key-change-in-production":
                logger.warning("⚠️ JWT_SECRET using default value - CHANGE THIS IN PRODUCTION!")
        return self._jwt_secret
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    
    # ========== FILE UPLOAD ==========
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    
    # ========== CORS ==========
    ALLOWED_ORIGINS: list = [
        "http://localhost:5500",
        "http://localhost:3000",
        "http://localhost:8080",
        "exp://localhost:8081",
        "https://wonderful-flower-0739f5710.7.azurestaticapps.net",
        "https://agreeable-pond-0372cb110.7.azurestaticapps.net",
        "https://mycampuscentral.in",
        "https://www.mycampuscentral.in",
    ]
    
    # ========== LUCKY NUMBER GAME ==========
    TEACHER_MIN_POINTS: int = 18
    TEACHER_MAX_POINTS: int = 81
    CELEBRATION_MIN_POINTS: int = 39
    CELEBRATION_MAX_POINTS: int = 93
    ULTRA_LUCKY_MAX: int = 40
    LUCKIER_MAX: int = 60
    
    # ========== RAZORPAY PAYMENT SETTINGS ==========
    # ✅ Lazy-loaded from Key Vault
    # ✅ No hardcoded test keys - only from Key Vault or environment
    # ✅ Warning logged if keys are missing
    _razorpay_key_id: Optional[str] = None
    _razorpay_key_secret: Optional[str] = None
    _razorpay_webhook_secret: Optional[str] = None
    
    @property
    def RAZORPAY_KEY_ID(self) -> str:
        """Lazy-load Razorpay Key ID from Key Vault."""
        if self._razorpay_key_id is None:
            self._razorpay_key_id = self._get_secret(
                "Razorpay-KeyId",
                fallback=os.getenv("RAZORPAY_KEY_ID", "")
            )
            if not self._razorpay_key_id:
                logger.warning("⚠️ RAZORPAY_KEY_ID is not configured. Payment will not work.")
        return self._razorpay_key_id
    
    @property
    def RAZORPAY_KEY_SECRET(self) -> str:
        """Lazy-load Razorpay Key Secret from Key Vault."""
        if self._razorpay_key_secret is None:
            self._razorpay_key_secret = self._get_secret(
                "Razorpay-KeySecret",
                fallback=os.getenv("RAZORPAY_KEY_SECRET", "")
            )
            if not self._razorpay_key_secret:
                logger.warning("⚠️ RAZORPAY_KEY_SECRET is not configured. Payment will not work.")
        return self._razorpay_key_secret
    
    @property
    def RAZORPAY_WEBHOOK_SECRET(self) -> str:
        """Lazy-load Razorpay Webhook Secret from Key Vault."""
        if self._razorpay_webhook_secret is None:
            self._razorpay_webhook_secret = self._get_secret(
                "Razorpay-Webhook-Secret",
                fallback=os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
            )
            if not self._razorpay_webhook_secret:
                logger.warning("⚠️ RAZORPAY_WEBHOOK_SECRET is not configured. Webhooks will not work.")
        return self._razorpay_webhook_secret
    
    # ========== TEST MODE ==========
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"
    TEST_PHONE_NUMBERS: list = os.getenv("TEST_PHONE_NUMBERS", "").split(",") if os.getenv("TEST_PHONE_NUMBERS") else []


# ========== CREATE SETTINGS INSTANCE ==========
settings = Settings()

# ========== LOG CONFIGURATION STATUS ==========
if settings.DEBUG:
    logger.info("🔧 Running in DEBUG mode")
    logger.info("   Database: %s", "SQLite (local)" if settings.USE_SQLITE else "Azure SQL")
    logger.info("   TEST_MODE: %s", settings.TEST_MODE)
    if settings.TEST_MODE:
        logger.info("   TEST_PHONE_NUMBERS: %s", settings.TEST_PHONE_NUMBERS)
else:
    logger.info("✅ Configuration loaded successfully")