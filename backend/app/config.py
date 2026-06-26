"""
backend/app/config.py
Phase 1 (June 18, 2026): Core app settings.
Phase 2 (June 19, 2026): Added TEST_MODE and TEST_PHONE_NUMBERS for OTP bypass.
Phase 3 (June 25, 2026): Integrated Azure Key Vault for secure secret management.
                         Database migrated from SQLite to Azure SQL.
                         Secrets now fetched from Key Vault with fallback to env vars.
Phase 4 (June 26, 2026): PERMANENT FIX - Azure SQL connection string optimized.
                         Added connection pooling configuration.
                         Enhanced error handling for database connections.
"""

import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Load environment variables from .env file (for local development)
load_dotenv()


class Settings:
    """
    Application settings loaded from environment variables and Azure Key Vault.
    
    For production: Secrets are fetched from Azure Key Vault.
    For local development: Falls back to environment variables or .env file.
    
    To use Key Vault in production, set these environment variables:
    - AZURE_KEY_VAULT_URL: The URL of your Key Vault instance
    - AZURE_TENANT_ID: Your Azure AD tenant ID (for authentication)
    - AZURE_CLIENT_ID: Service principal client ID (if using SP)
    - AZURE_CLIENT_SECRET: Service principal secret (if using SP)
    """
    
    # ========== APP SETTINGS ==========
    APP_NAME: str = "Campus Central API"
    """Name of the application."""
    
    APP_VERSION: str = "1.0.0"
    """Version of the application."""
    
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    """Enable debug mode. Set to 'false' in production."""
    
    # ========== KEY VAULT CONFIGURATION ==========
    KEY_VAULT_URL: str = os.getenv("AZURE_KEY_VAULT_URL", "https://campuscentral-keyvalut.vault.azure.net/")
    """Azure Key Vault URL for fetching secrets in production."""
        # Initialize Key Vault client (lazy-loaded to avoid startup failures in local dev)
    _secret_client = None
    _secret_cache = {}  # ✅ NEW: Cache for secrets to reduce Key Vault calls
    
    @classmethod
    def _get_secret_client(cls):
        """Lazy-initialize the Key Vault client."""
        if cls._secret_client is None:
            try:
                credential = DefaultAzureCredential()
                cls._secret_client = SecretClient(vault_url=cls.KEY_VAULT_URL, credential=credential)
            except Exception as e:
                print(f"⚠️ Failed to initialize Key Vault client: {e}")
                cls._secret_client = None
        return cls._secret_client
    
    @classmethod
    def _get_secret(cls, secret_name: str, fallback: str = None) -> str:
        """
        Fetch a secret from Azure Key Vault with fallback to environment variable.
        ✅ IMPROVED: Now caches secrets to reduce Key Vault calls.
        
        Args:
            secret_name: Name of the secret in Key Vault
            fallback: Fallback value if secret cannot be fetched
            
        Returns:
            The secret value or fallback
        """
        # ✅ Check cache first
        if secret_name in cls._secret_cache:
            return cls._secret_cache[secret_name]
        
        client = cls._get_secret_client()
        if client:
            try:
                value = client.get_secret(secret_name).value
                cls._secret_cache[secret_name] = value  # Cache it
                return value
            except Exception as e:
                print(f"⚠️ Failed to fetch secret '{secret_name}': {e}")
        
        # Fallback to environment variable
        env_value = os.getenv(secret_name)
        if env_value:
            cls._secret_cache[secret_name] = env_value
            return env_value
        
        if fallback:
            cls._secret_cache[secret_name] = fallback
            return fallback
        
        print(f"⚠️ No value found for '{secret_name}'. Using empty string.")
        return ""
        # ========== DATABASE (Azure SQL) ==========
    DB_USER: str = os.getenv("DB_USER", "campusadmin")
    """Azure SQL database username."""
    
    DB_HOST: str = os.getenv("DB_HOST", "campuscentral-sql-server.database.windows.net")
    """Azure SQL server hostname."""
    
    DB_NAME: str = os.getenv("DB_NAME", "campuscentral_sql_db")
    """Azure SQL database name."""
    
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    """ODBC driver for Azure SQL connection."""
    
    # Fetch password from Key Vault (fallback to env var)
    DB_PASSWORD: str = ""
    """Azure SQL database password (fetched from Key Vault)."""
    
    @classmethod
    def _get_db_password(cls):
        """Fetch DB password from Key Vault."""
        return cls._get_secret("DB-Password", fallback=os.getenv("DB_PASSWORD", ""))
    
    # ========== SECURITY ==========
    # Fetch JWT secret from Key Vault (fallback to env var)
    JWT_SECRET: str = ""
    """Secret key for JWT token signing (fetched from Key Vault)."""
    
    @classmethod
    def _get_jwt_secret(cls):
        """Fetch JWT secret from Key Vault."""
        return cls._get_secret("JWT-Secret", fallback=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production"))
    
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
    # Fetch Razorpay keys from Key Vault (fallback to env var)
    RAZORPAY_KEY_ID: str = ""
    """Razorpay API Key ID for payment processing (fetched from Key Vault)."""
    
    RAZORPAY_KEY_SECRET: str = ""
    """Razorpay API Key Secret for payment processing (fetched from Key Vault)."""
    
    RAZORPAY_WEBHOOK_SECRET: str = ""
    """Razorpay webhook secret for verifying webhook signatures (fetched from Key Vault)."""
    
    @classmethod
    def _get_razorpay_key_id(cls):
        return cls._get_secret("Razorpay-KeyId", fallback=os.getenv("RAZORPAY_KEY_ID", "rzp_test_T0KRH1p12BN6S3"))
    
    @classmethod
    def _get_razorpay_key_secret(cls):
        return cls._get_secret("Razorpay-KeySecret", fallback=os.getenv("RAZORPAY_KEY_SECRET", "13NK59ubLhjQAp75VzkLm803"))
    
    @classmethod
    def _get_razorpay_webhook_secret(cls):
        return cls._get_secret("Razorpay-Webhook-Secret", fallback=os.getenv("RAZORPAY_WEBHOOK_SECRET", "your_webhook_secret_here"))
    
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
    # ========== CREATE SETTINGS INSTANCE ==========
settings = Settings()

# ========== FETCH SECRETS AFTER INSTANCE CREATION ==========
settings.DB_PASSWORD = settings._get_db_password()
settings.JWT_SECRET = settings._get_jwt_secret()
settings.RAZORPAY_KEY_ID = settings._get_razorpay_key_id()
settings.RAZORPAY_KEY_SECRET = settings._get_razorpay_key_secret()
settings.RAZORPAY_WEBHOOK_SECRET = settings._get_razorpay_webhook_secret()
# ========== ✅ PERMANENT FIX: BUILD DATABASE URL ==========
def get_database_url() -> str:
    """
    ✅ PERMANENT FIX for Azure SQL connection with Managed Identity.
    
    This function builds the correct connection string for ODBC Driver 18
    on Azure App Service Linux with Managed Identity authentication.
    
    CRITICAL: The Authentication parameter MUST be 'ActiveDirectoryMSI'
    (NOT 'ActiveDirectoryManagedIdentity') for ODBC Driver 18.
    
    Falls back to SQLite for local development.
    """
    db_host = settings.DB_HOST
    db_name = settings.DB_NAME
    db_driver = settings.DB_DRIVER
    
    if db_host:
        # ✅ CORRECT format for Azure SQL with Managed Identity
        # ODBC Driver 18 on Linux requires this exact format
        return (
            f"mssql+pyodbc://{db_host}/{db_name}"
            f"?driver={db_driver}"
            f"&Encrypt=yes"
            f"&TrustServerCertificate=no"
            f"&ConnectionTimeout=30"
            f"&Authentication=ActiveDirectoryMSI"  # ✅ CORRECT - DO NOT CHANGE
        )
    
    # Fallback for local development
    sqlite_path = os.getenv("SQLITE_PATH", "sqlite:///./campus_central.db")
    print("⚠️ Using SQLite fallback (Azure SQL credentials not available)")
    return sqlite_path


# Set the database URL on the settings object
settings.DATABASE_URL = get_database_url()
# ========== DEVELOPMENT HELPER ==========
if settings.DEBUG:
    print("🔧 Running in DEBUG mode")
    # ✅ Mask password in database URL
    db_url = settings.DATABASE_URL
    if '@' in db_url:
        # Split at @ to separate credentials from host
        parts = db_url.split('@')
        # Mask the password part (between : and @)
        if '://' in parts[0]:
            protocol = parts[0].split('://')[0] + '://'
            creds = parts[0].split('://')[1]
            if ':' in creds:
                user = creds.split(':')[0]
                db_url = f"{protocol}{user}:****@{parts[1]}"
    print(f"   Database: {db_url}")
    print(f"   TEST_MODE: {settings.TEST_MODE}")
    if settings.TEST_MODE:
        print(f"   TEST_PHONE_NUMBERS: {settings.TEST_PHONE_NUMBERS}")

# ========== ✅ ADDED: Connection validation on startup ==========
def validate_database_connection() -> bool:
    """
    ✅ NEW: Validate database connection on startup.
    This helps catch connection issues early.
    """
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"⚠️ Database connection validation failed: {e}")
        return False

# Run validation on import (non-blocking)
try:
    if settings.DEBUG:
        validate_database_connection()
except Exception:
    pass  # Silently fail during import