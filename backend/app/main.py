"""
backend/app/main.py
Campus Central API - FastAPI entry point

Phase 1 (June 18, 2026): Initial deployment.
Phase 2 (June 19, 2026): CORS fix + Azure deployment stability + preflight handling.
Phase 3 (June 25, 2026): Azure Key Vault integration for secrets.
                         Azure SQL Database (replaces SQLite).
                         JWT_SECRET now fetched from Key Vault.
                         Database URL built dynamically from Key Vault secrets.
"""

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from sqlalchemy.orm import Session
import os
import time
import logging

from app.config import settings
from app.database import engine, Base, get_db

# ========== LOGGING SETUP ==========
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================
# IMPORT ALL MODELS (REQUIRED FOR TABLE CREATION)
# ============================================================
from app.models import (
    User,
    TeacherGroup,
    CelebrationGroup,
    GroupMember,
    Message,
    Payment,
    SuccessStory,
    OTPCode,
    SocialPost,
    SocialComment,
    SocialLike,
    ConnectionRequest,
    FriendStory
)

# ============================================================
# CREATE TABLES (Azure SQL or SQLite fallback)
# ============================================================
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/verified successfully")
    logger.info(f"   Database: {'Azure SQL' if 'mssql' in settings.DATABASE_URL else 'SQLite (fallback)'}")
except Exception as e:
    logger.error(f"❌ Failed to create database tables: {e}")

# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ============================================================
# CORS (MUST BE FIRST MIDDLEWARE)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # ✅ Uses your updated list from config.py
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# GLOBAL REQUEST LOGGER
# ============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with method, path, status, and duration."""
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.0f}ms)")
    return response

# ============================================================
# IMPORTANT: HANDLE PREFLIGHT (OPTIONS REQUESTS)
# ============================================================
@app.options("/{path:path}")
async def preflight_handler(path: str):
    """Handle CORS preflight OPTIONS requests."""
    return Response(status_code=200)

# ============================================================
# OPTIONAL: IP WHITELIST (DISABLED SAFE FOR AZURE)
# ============================================================
"""
from starlette.middleware.base import BaseHTTPMiddleware

ALLOWED_IPS = {"152.57.19.112", "152.57.3.55"}

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        if ip not in ALLOWED_IPS:
            return Response("Forbidden", status_code=403)
        return await call_next(request)

# app.add_middleware(IPWhitelistMiddleware)
"""

# ============================================================
# STATIC FILES
# ============================================================
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ============================================================
# ROUTERS
# ============================================================
from routers import (
    auth,
    groups,
    dashboard,
    search,
    stories,
    admin,
    batchmate,
    business,
    startup,
    hive,
    crush,
    avatar,
    forum,
    marriage,
    messages,
    public,
    findmyfriend,
    social_posts,
    users,
    connections,
    mood_memory,
    friend_search,
)

from routers.payment import router as payment_router

# ========== INCLUDE ALL ROUTERS ==========
app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(stories.router)
app.include_router(admin.router)

app.include_router(batchmate.router)
app.include_router(business.router)
app.include_router(startup.router)
app.include_router(hive.router)
app.include_router(crush.router)
app.include_router(avatar.router)
app.include_router(forum.router)
app.include_router(marriage.router)
app.include_router(messages.router)
app.include_router(public.router)
app.include_router(findmyfriend.router)
app.include_router(payment_router)
app.include_router(social_posts.router)
app.include_router(users.router)
app.include_router(connections.router)
app.include_router(mood_memory.router)
app.include_router(friend_search.router)

# ============================================================
# ROOT ENDPOINT
# ============================================================
@app.get("/")
def root():
    """Root endpoint with database status."""
    return {
        "message": "Welcome to Campus Central API",
        "status": "running",
        "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite (fallback)",
        "version": settings.APP_VERSION
    }

# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health")
def health():
    """Health check endpoint for Azure monitoring."""
    return {
        "status": "healthy",
        "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite (fallback)"
    }

# ============================================================
# PUBLIC JOIN
# ============================================================
@app.get("/join/{group_id}")
def join_group(group_id: str, db: Session = Depends(get_db)):
    """
    Public endpoint to check group details before joining.
    Returns group type and member count.
    """
    from app.models import TeacherGroup, CelebrationGroup, GroupMember

    teacher = db.query(TeacherGroup).filter_by(group_id=group_id).first()
    if teacher:
        count = db.query(GroupMember).filter_by(teacher_group_id=teacher.id).count()
        return {
            "success": True,
            "type": "teacher",
            "group_id": teacher.group_id,
            "member_count": count,
        }

    celebration = db.query(CelebrationGroup).filter_by(group_id=group_id).first()
    if celebration:
        count = db.query(GroupMember).filter_by(celebration_group_id=celebration.id).count()
        return {
            "success": True,
            "type": "celebration",
            "group_id": celebration.group_id,
            "member_count": count,
        }

    return {"success": False, "message": "Group not found"}

# ============================================================
# VERSION
# ============================================================
@app.get("/api/version")
def version():
    """Returns the current API version and available features."""
    return {
        "version": settings.APP_VERSION,
        "features": [
            "Batchmate Finder",
            "Crush Corner",
            "Startup Nest",
            "Mood & Memory",
            "Find My Friend",
        ],
        "database": "Azure SQL" if "mssql" in settings.DATABASE_URL else "SQLite (fallback)"
    }

# ============================================================
# TEMPORARY: INIT DATABASE TABLES (ONE-TIME USE)
# ============================================================
@app.get("/init-db")
def init_database():
    """One-time endpoint to create all tables (useful for first deployment)."""
    try:
        Base.metadata.create_all(bind=engine)
        return {"status": "✅ All tables created successfully"}
    except Exception as e:
        return {"status": "❌ Failed to create tables", "error": str(e)}

# ============================================================
# RUN LOCALLY ONLY
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)