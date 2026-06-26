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
    """
    
    # ========== APP SETTINGS ==========
    APP_NAME: str = "Campus Central API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ========== KEY VAULT CONFIGURATION ==========
    KEY_VAULT_URL: str = os.getenv("AZURE_KEY_VAULT_URL", "https://campuscentral-keyvalut.vault.azure.net/")
    _secret_client = None
    _secret_cache = {}
    
    @classmethod
    def _get_secret_client(cls):
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
        if secret_name in cls._secret_cache:
            return cls._secret_cache[secret_name]
        
        client = cls._get_secret_client()
        if client:
            try:
                value = client.get_secret(secret_name).value
                cls._secret_cache[secret_name] = value
                return value
            except Exception as e:
                print(f"⚠️ Failed to fetch secret '{secret_name}': {e}")
        
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
    DB_HOST: str = os.getenv("DB_HOST", "campuscentral-sql-server.database.windows.net")
    DB_NAME: str = os.getenv("DB_NAME", "campuscentral_sql_db")
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    DB_PASSWORD: str = ""
    
    @classmethod
    def _get_db_password(cls):
        return cls._get_secret("DB-Password", fallback=os.getenv("DB_PASSWORD", ""))
    
    # ========== SECURITY ==========
    JWT_SECRET: str = ""
    
    @classmethod
    def _get_jwt_secret(cls):
        return cls._get_secret("JWT-Secret", fallback=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production"))
    
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
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    
    @classmethod
    def _get_razorpay_key_id(cls):
        return cls._get_secret("Razorpay-KeyId", fallback=os.getenv("RAZORPAY_KEY_ID", "rzp_test_T0KRH1p12BN6S3"))
    
    @classmethod
    def _get_razorpay_key_secret(cls):
        return cls._get_secret("Razorpay-KeySecret", fallback=os.getenv("RAZORPAY_KEY_SECRET", "13NK59ubLhjQAp75VzkLm803"))
    
    @classmethod
    def _get_razorpay_webhook_secret(cls):
        return cls._get_secret("Razorpay-Webhook-Secret", fallback=os.getenv("RAZORPAY_WEBHOOK_SECRET", "your_webhook_secret_here"))
    
    # ========== TEST MODE ==========
    TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"
    TEST_PHONE_NUMBERS: list = os.getenv("TEST_PHONE_NUMBERS", "").split(",") if os.getenv("TEST_PHONE_NUMBERS") else []


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
    db_host = settings.DB_HOST
    db_name = settings.DB_NAME
    db_driver = settings.DB_DRIVER
    
    if db_host:
        return (
            f"mssql+pyodbc://{db_host}/{db_name}"
            f"?driver={db_driver}"
            f"&Encrypt=yes"
            f"&TrustServerCertificate=no"
            f"&ConnectionTimeout=30"
            f"&Authentication=ActiveDirectoryMSI"
        )
    
    sqlite_path = os.getenv("SQLITE_PATH", "sqlite:///./campus_central.db")
    print("⚠️ Using SQLite fallback (Azure SQL credentials not available)")
    return sqlite_path


settings.DATABASE_URL = get_database_url()

# ========== DEVELOPMENT HELPER ==========
if settings.DEBUG:
    print("🔧 Running in DEBUG mode")
    db_url = settings.DATABASE_URL
    if '@' in db_url:
        parts = db_url.split('@')
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
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"⚠️ Database connection validation failed: {e}")
        return False


try:
    if settings.DEBUG:
        validate_database_connection()
except Exception:
    pass