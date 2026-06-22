"""
backend/app/main.py
Updated: CORS fix + Azure deployment stability + preflight handling
"""

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from sqlalchemy.orm import Session
import os
import time

from app.config import settings
from app.database import engine, Base, get_db
import app.models

# ============================================================
# CREATE TABLES
# ============================================================
Base.metadata.create_all(bind=engine)

# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# ============================================================
# CORS (MUST BE FIRST MIDDLEWARE)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# GLOBAL REQUEST LOGGER
# ============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    print(f"{request.method} {request.url.path} -> {response.status_code} ({duration:.0f}ms)")
    return response

# ============================================================
# IMPORTANT: HANDLE PREFLIGHT (OPTIONS REQUESTS)
# ============================================================
@app.options("/{path:path}")
async def preflight_handler(path: str):
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
    auth, groups, dashboard, search, stories, admin,
    batchmate, business, startup, hive, crush, avatar,
    forum, marriage, messages, public, findmyfriend,
    social_posts, users, connections, mood_memory,
    friend_search
)

from routers.payment import router as payment_router

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
# ROOT
# ============================================================
@app.get("/")
def root():
    return {
        "message": "Welcome to Campus Central API",
        "status": "running"
    }

# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health")
def health():
    return {"status": "healthy"}

# ============================================================
# PUBLIC JOIN
# ============================================================
@app.get("/join/{group_id}")
def join_group(group_id: str, db: Session = Depends(get_db)):
    from app.models import TeacherGroup, CelebrationGroup, GroupMember

    teacher = db.query(TeacherGroup).filter_by(group_id=group_id).first()
    if teacher:
        count = db.query(GroupMember).filter_by(teacher_group_id=teacher.id).count()
        return {
            "success": True,
            "type": "teacher",
            "group_id": teacher.group_id,
            "member_count": count
        }

    celebration = db.query(CelebrationGroup).filter_by(group_id=group_id).first()
    if celebration:
        count = db.query(GroupMember).filter_by(celebration_group_id=celebration.id).count()
        return {
            "success": True,
            "type": "celebration",
            "group_id": celebration.group_id,
            "member_count": count
        }

    return {"success": False, "message": "Group not found"}

# ============================================================
# VERSION
# ============================================================
@app.get("/api/version")
def version():
    return {
        "version": settings.APP_VERSION,
        "features": [
            "Batchmate Finder",
            "Crush Corner",
            "Startup Nest",
            "Mood & Memory",
            "Find My Friend"
        ]
    }

# ============================================================
# RUN LOCALLY ONLY
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)