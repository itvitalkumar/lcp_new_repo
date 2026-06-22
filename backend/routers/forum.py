from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/forum", tags=["Teen Space Forum"])

# ============ MODELS ============
class PostCreate(BaseModel):
    title: str
    content: str
    category: str

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    author_name: str
    author_college: Optional[str]
    created_at: str
    reply_count: int
    likes: int

class ReplyCreate(BaseModel):
    post_id: int
    content: str

class ReplyResponse(BaseModel):
    id: int
    post_id: int
    author_name: str
    content: str
    created_at: str


# In-memory storage (replace with database tables)
posts_db = []
posts_counter = 0
replies_db = []
replies_counter = 0
post_likes_db = []


@router.post("/post", response_model=dict)
def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new forum post"""
    global posts_counter
    posts_counter += 1
    
    posts_db.append({
        "id": posts_counter,
        "user_id": current_user.id,
        "author_name": current_user.full_name,
        "author_college": getattr(current_user, "college", None),
        "title": data.title,
        "content": data.content,
        "category": data.category,
        "likes": 0,
        "created_at": datetime.now().isoformat(),
        "is_active": True
    })
    
    return {
        "success": True,
        "id": posts_counter,
        "message": "Post created successfully"
    }


@router.get("/posts", response_model=List[PostResponse])
def get_posts(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Number of posts"),
    db: Session = Depends(get_db)
):
    """Get all forum posts (newest first)"""
    
    results = [p for p in posts_db if p.get("is_active", True)]
    
    if category and category != "all":
        results = [p for p in results if p["category"] == category]
    
    # Sort by newest first
    results.sort(key=lambda x: x["created_at"], reverse=True)
    results = results[:limit]
    
    # Add reply counts
    for post in results:
        reply_count = len([r for r in replies_db if r["post_id"] == post["id"]])
        post["reply_count"] = reply_count
    
    return [
        PostResponse(
            id=p["id"],
            title=p["title"],
            content=p["content"],
            category=p["category"],
            author_name=p["author_name"],
            author_college=p.get("author_college"),
            created_at=p["created_at"],
            reply_count=p.get("reply_count", 0),
            likes=p.get("likes", 0)
        )
        for p in results
    ]


@router.get("/post/{post_id}", response_model=PostResponse)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Get single post with details"""
    
    post = next((p for p in posts_db if p["id"] == post_id and p.get("is_active", True)), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    reply_count = len([r for r in replies_db if r["post_id"] == post_id])
    
    return PostResponse(
        id=post["id"],
        title=post["title"],
        content=post["content"],
        category=post["category"],
        author_name=post["author_name"],
        author_college=post.get("author_college"),
        created_at=post["created_at"],
        reply_count=reply_count,
        likes=post.get("likes", 0)
    )


@router.post("/reply", response_model=dict)
def create_reply(
    data: ReplyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a reply to a post"""
    global replies_counter
    replies_counter += 1
    
    # Verify post exists
    post = next((p for p in posts_db if p["id"] == data.post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    replies_db.append({
        "id": replies_counter,
        "post_id": data.post_id,
        "user_id": current_user.id,
        "author_name": current_user.full_name,
        "content": data.content,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "id": replies_counter,
        "message": "Reply added successfully"
    }


@router.get("/replies/{post_id}", response_model=List[ReplyResponse])
def get_replies(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Get all replies for a post"""
    
    post_replies = [r for r in replies_db if r["post_id"] == post_id]
    post_replies.sort(key=lambda x: x["created_at"])
    
    return [
        ReplyResponse(
            id=r["id"],
            post_id=r["post_id"],
            author_name=r["author_name"],
            content=r["content"],
            created_at=r["created_at"]
        )
        for r in post_replies
    ]


@router.post("/like/{post_id}")
def like_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like a post"""
    
    post = next((p for p in posts_db if p["id"] == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post["likes"] = post.get("likes", 0) + 1
    
    return {"success": True, "likes": post["likes"]}


@router.get("/categories")
def get_categories():
    """Get available forum categories"""
    
    return {
        "categories": [
            {"id": "General", "name": "General Discussion", "icon": "💬"},
            {"id": "Career", "name": "Career & Jobs", "icon": "💼"},
            {"id": "Academics", "name": "Academics & Exams", "icon": "📚"},
            {"id": "Mental Health", "name": "Mental Health & Wellness", "icon": "🧠"},
            {"id": "Relationships", "name": "Friends & Relationships", "icon": "💕"},
            {"id": "Skills", "name": "Skills & Learning", "icon": "🎓"}
        ]
    }


@router.get("/stats")
def get_forum_stats(db: Session = Depends(get_db)):
    """Get forum statistics"""
    
    return {
        "total_posts": len(posts_db),
        "total_replies": len(replies_db),
        "total_likes": sum(p.get("likes", 0) for p in posts_db),
        "active_users": len(set(p["user_id"] for p in posts_db))
    }