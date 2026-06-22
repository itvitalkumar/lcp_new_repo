"""
backend/app/main.py
Phase 1 version: Initial deployment (June 18, 2026) - core app setup with all routers.
Phase 2 update (June 19, 2026): Added IP whitelist middleware for restricting access during testing.
Docstrings added for all functions and middleware.
"""

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import os
import time

from app.config import settings
from app.database import engine, Base, get_db
import app.models

# Create database tables
Base.metadata.create_all(bind=engine)

# ============================================================
# INITIALIZE FASTAPI APP
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Campus Central Backend API - Gift Teacher & Celebrate Together | Batchmate Finder | Family Business | Startup Nest | Keep the Hive | Crush Corner | Avatar Studio | Teen Space Forum | Marriage Staffing | Find My Friend | Mood & Memory"
)

# ============================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware that logs all incoming API requests with status and duration.
    Useful for debugging and monitoring API usage.
    """
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    print(f"{request.method} {request.url.path} - {response.status_code} - {duration_ms:.0f}ms")
    return response

# ============================================================
# IP WHITELIST MIDDLEWARE (Phase 2 - Added June 19, 2026)
# ============================================================
# Allows only specified IP addresses to access the API.
# All other IPs receive a 403 Forbidden response.
# This is useful for restricting access during testing/development.
# ============================================================

# Replace with your actual public IP(s)
# You can find your public IP at: https://whatismyip.com
ALLOWED_IPS = {
    "152.57.19.112",   # Your original IP (home/library)
    "152.57.3.55",     # Your current IP (home)
    # Add more IPs as needed, e.g., "203.0.113.5"
}

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict API access to a specific list of allowed IPs.
    """
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        # Check if the client IP is in the allowed list
        if client_ip not in ALLOWED_IPS:
            raise HTTPException(
                status_code=403, 
                detail="Access denied. Your IP is not authorized to access this resource."
            )
        return await call_next(request)

# Add the IP whitelist middleware to the app (must be added before CORS)
# commented below line just for making the page live to razorpay, i shall opn the below line once they approve my id in razor pay
# app.add_middleware(IPWhitelistMiddleware)

# ============================================================
# CORS MIDDLEWARE
# ============================================================
# Allow all origins for simplicity, consider restricting in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        # Keep any existing origins if they exist
    ],
    #allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STATIC FILES & UPLOADS
# ============================================================
# Create uploads directory if not exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ============================================================
# IMPORT ALL ROUTERS
# ============================================================
from routers import auth, groups, dashboard, search, stories, admin
from routers import batchmate, business, startup, hive, crush, avatar, forum, marriage, messages, public
from routers import findmyfriend
from routers.payment import router as payment_router
from routers import social_posts
from routers import users
from routers import connections
from routers import mood_memory
from routers import friend_search

# ============================================================
# INCLUDE ALL ROUTERS
# ============================================================
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
app.include_router(social_posts.router)   # Keep for backward compatibility / admin
app.include_router(users.router)
app.include_router(connections.router)

# New separate routers
app.include_router(mood_memory.router)      # /api/mood-memory/*
app.include_router(friend_search.router)    # /api/friend-search/*

# ============================================================
# ROOT ENDPOINTS
# ============================================================
@app.get("/")
def root():
    """
    Root endpoint that provides an overview of the API and all available endpoints.
    Used as a health check and for API discovery.
    """
    return {
        "message": "Welcome to Campus Central API",
        "version": settings.APP_VERSION,
        "status": "running",
        "endpoints": {
            "auth": ["/api/auth/signup", "/api/auth/login", "/api/auth/me"],
            "groups": ["/api/groups/teacher/create", "/api/groups/celebration/create", "/api/groups/lucky-game"],
            "dashboard": ["/api/dashboard/student", "/api/dashboard/teacher/{teacher_id}"],
            "search": ["/api/search/groups", "/api/search/districts", "/api/search/group/{group_id}"],
            "stories": ["/api/stories/", "/api/stories/create"],
            "batchmate": ["/api/batchmate/register", "/api/batchmate/search", "/api/batchmate/connect"],
            "business": ["/api/business/create", "/api/business/list"],
            "startup": ["/api/startup/create", "/api/startup/list", "/api/startup/interest"],
            "hive": ["/api/hive/contribute", "/api/hive/stats", "/api/hive/testimonials"],
            "crush": ["/api/crush/quiz/submit", "/api/crush/name/generate", "/api/crush/quiz/leaderboard"],
            "avatar": ["/api/avatar/create", "/api/avatar/gallery", "/api/avatar/my-avatars"],
            "forum": ["/api/forum/post", "/api/forum/posts", "/api/forum/reply"],
            "marriage": ["/api/marriage/post-job", "/api/marriage/jobs", "/api/marriage/apply", "/api/marriage/activate/{job_id}"],
            "messages": ["/api/messages/send", "/api/messages/{group_id}", "/api/messages/{message_id}"],
            "findmyfriend": ["/api/findmyfriend/create", "/api/findmyfriend/search", "/api/findmyfriend/reveal/{story_id}"],
            "mood_memory": ["/api/mood-memory/posts", "/api/mood-memory/posts/create", "/api/mood-memory/posts/{post_id}/like", "/api/mood-memory/posts/{post_id}/comment"],
            "friend_search": ["/api/friend-search/posts", "/api/friend-search/posts/create", "/api/friend-search/posts/{post_id}/like", "/api/friend-search/posts/{post_id}/comment"]
        }
    }

@app.get("/health")
def health_check():
    """Simple health check endpoint to verify the API is running."""
    return {"status": "healthy"}

@app.get("/api/public/groups")
def public_groups():
    """
    Public groups endpoint - intended for caching and public access.
    """
    return {"message": "Public groups endpoint - implement caching here"}

@app.get("/api/version")
def get_version():
    """
    Returns the API version and a list of available features.
    """
    return {
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "features": [
            "Thank Teacher (₹18-₹81)",
            "Celebrate Together (₹36-₹93)",
            "Batchmate Finder (FREE)",
            "Avatar Studio (FREE)",
            "Crush Corner (₹1)",
            "Family Business Showcase (FREE)",
            "Ants' Startup Nest (FREE)",
            "Keep the Hive Buzzing (Voluntary)",
            "Teen Space Forum (FREE)",
            "Marriage Staffing Marketplace (₹99/post)",
            "Find My Friend (FREE - AI Powered)",
            "Mood & Memory (FREE - Share Campus Stories)"
        ]
    }

# ============================================================
# PUBLIC JOIN ENDPOINT
# ============================================================
@app.get("/join/{group_id}")
async def get_join_page(
    group_id: str,
    db: Session = Depends(get_db)
):
    """
    Public endpoint for joining a group via invite link.
    Returns group details for display on the frontend.
    """
    from app.models import TeacherGroup, CelebrationGroup, GroupMember
    
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        member_count = db.query(GroupMember).filter(GroupMember.teacher_group_id == teacher_group.id).count()
        return {
            "success": True,
            "type": "teacher",
            "group_id": teacher_group.group_id,
            "name": teacher_group.teacher_name,
            "college": teacher_group.college,
            "district": teacher_group.district,
            "event_date": teacher_group.event_date,
            "venue": teacher_group.venue,
            "member_count": member_count,
            "status": teacher_group.status,
            "is_active": teacher_group.status == "active"
        }
    
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        member_count = db.query(GroupMember).filter(GroupMember.celebration_group_id == celebration_group.id).count()
        return {
            "success": True,
            "type": "celebration",
            "group_id": celebration_group.group_id,
            "name": celebration_group.title,
            "location": celebration_group.location,
            "district": celebration_group.district,
            "event_date": celebration_group.event_date,
            "venue": celebration_group.venue,
            "member_count": member_count,
            "status": celebration_group.status,
            "is_active": celebration_group.status == "active"
        }
    
    return {
        "success": False,
        "message": "Group not found. The invite link may be invalid or the group has been deleted.",
        "group_id": group_id
    }

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1",
        port=8000,
        reload=True
    )