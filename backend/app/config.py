"""
backend/app/config.py
Campus Central API - Configuration & Secrets Management

Phase 1 (June 18, 2026): Core app settings.
Phase 2 (June 19, 2026): Added TEST_MODE and TEST_PHONE_NUMBERS for OTP bypass.
Phase 3 (June 25, 2026): Integrated Azure Key Vault for secure secret management.
                         Database migrated from SQLite to Azure SQL.
                         Secrets now fetched from Key Vault with fallback to env vars.
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
    KEY_VAULT_URL: str = os.getenv("AZURE_KEY_VAULT_URL", "https://campuscentral-keyvault.vault.azure.net/")
    """Azure Key Vault URL for fetching secrets in production."""
    
    # Initialize Key Vault client (lazy-loaded to avoid startup failures in local dev)
    _secret_client = None
    
    @classmethod
    def _get_secret_client(cls):
        """
        Lazy-initialize the Key Vault client.
        
        Returns:
            SecretClient or None: The Key Vault client if initialized successfully.
        """
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
        
        Args:
            secret_name: Name of the secret in Key Vault.
            fallback: Fallback value if secret cannot be fetched.
            
        Returns:
            str: The secret value or fallback.
        """
        client = cls._get_secret_client()
        if client:
            try:
                return client.get_secret(secret_name).value
            except Exception as e:
                print(f"⚠️ Failed to fetch secret '{secret_name}': {e}")
        # Fallback to environment variable
        env_value = os.getenv(secret_name)
        if env_value:
            return env_value
        if fallback:
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
    DB_PASSWORD: str = _get_secret.__func__(
        Settings, "DB-Password", 
        fallback=os.getenv("DB_PASSWORD", "")
    )
    """Azure SQL database password (fetched from Key Vault)."""
    
    # ========== DATABASE URL (DYNAMIC) ==========
    @property
    def DATABASE_URL(self) -> str:
        """
        Build the Azure SQL connection URL using fetched credentials.
        Falls back to SQLite for local development if Key Vault is unavailable.
        
        Returns:
            str: The database connection URL.
        """
        if self.DB_PASSWORD and self.DB_HOST:
            return (
                f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}/{self.DB_NAME}"
                f"?driver={self.DB_DRIVER}&Encrypt=yes&TrustServerCertificate=no&ConnectionTimeout=30"
            )
        # Fallback to SQLite for local development
        sqlite_path = os.getenv("SQLITE_PATH", "sqlite:///./campus_central.db")
        print("⚠️ Using SQLite fallback (Azure SQL credentials not available)")
        return sqlite_path
    
    # ========== SECURITY ==========
    # Fetch JWT secret from Key Vault (fallback to env var)
    JWT_SECRET: str = _get_secret.__func__(
        Settings, "JWT-Secret",
        fallback=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
    )
    """Secret key for JWT token signing (fetched from Key Vault)."""
    
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
    RAZORPAY_KEY_ID: str = _get_secret.__func__(
        Settings, "Razorpay-KeyId",
        fallback=os.getenv("RAZORPAY_KEY_ID", "rzp_test_T0KRH1p12BN6S3")
    )
    """Razorpay API Key ID for payment processing (fetched from Key Vault)."""
    
    RAZORPAY_KEY_SECRET: str = _get_secret.__func__(
        Settings, "Razorpay-KeySecret",
        fallback=os.getenv("RAZORPAY_KEY_SECRET", "13NK59ubLhjQAp75VzkLm803")
    )
    """Razorpay API Key Secret for payment processing (fetched from Key Vault)."""
    
    RAZORPAY_WEBHOOK_SECRET: str = _get_secret.__func__(
        Settings, "Razorpay-Webhook-Secret",
        fallback=os.getenv("RAZORPAY_WEBHOOK_SECRET", "your_webhook_secret_here")
    )
    """Razorpay webhook secret for verifying webhook signatures (fetched from Key Vault)."""
    
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

# ========== DEVELOPMENT HELPER ==========
if settings.DEBUG:
    print("🔧 Running in DEBUG mode")
    print(f"   Database: {settings.DATABASE_URL.split('@')[0] if '@' in settings.DATABASE_URL else 'SQLite'}")
    print(f"   TEST_MODE: {settings.TEST_MODE}")
    if settings.TEST_MODE:
        print(f"   TEST_PHONE_NUMBERS: {settings.TEST_PHONE_NUMBERS}")