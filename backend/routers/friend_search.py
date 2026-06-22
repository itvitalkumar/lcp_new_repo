from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil

from app.database import get_db
from app.models import User, SocialPost, SocialComment, SocialLike
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/friend-search", tags=["Find My Friend"])

# Helper to save uploaded photo
def save_photo(file: UploadFile) -> str:
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"friend_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return f"/uploads/{filename}"


@router.get("/posts", response_model=List[dict])
def get_friend_search_posts(
    category: Optional[str] = Query(None, description="Filter by category"),
    privacy: Optional[str] = Query(None, description="Filter by privacy: 'public' or 'private'"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get ONLY Friend Search posts."""
    
    # ✅ ONLY Friend Search posts (college is NOT "Mood & Memory")
    query = db.query(SocialPost).filter(SocialPost.college != "Mood & Memory")
    
    # Filter by privacy
    if privacy == "private":
        if not current_user:
            return []
        query = query.filter(
            SocialPost.privacy == "private",
            SocialPost.user_id == current_user.id
        )
    else:
        if current_user:
            query = query.filter(
                (SocialPost.privacy == "public") | 
                ((SocialPost.privacy == "private") & (SocialPost.user_id == current_user.id))
            )
        else:
            query = query.filter(SocialPost.privacy == "public")
    
    # Apply category filter if provided
    if category:
        query = query.filter(SocialPost.category == category)
    
    posts = query.order_by(SocialPost.created_at.desc()).all()
        
    result = []
    for p in posts:
        comments = db.query(SocialComment).filter(SocialComment.post_id == p.id).order_by(SocialComment.created_at.asc()).all()
        
        result.append({
            "id": p.id,
            "user_id": p.user_id,
            "user_name": p.user_name if not p.anonymous else "Anonymous",
            "college": p.college,
            "batch": p.batch,
            "message": p.message,
            "title": p.title if hasattr(p, 'title') else "",
            "category": p.category if hasattr(p, 'category') else "friend",
            "photo": p.photo,
            "video_url": p.video_url,
            "privacy": p.privacy,
            "anonymous": p.anonymous,
            "likes_count": p.likes_count,
            "created_at": p.created_at.isoformat(),
            "comments": [{"id": c.id, "user_name": c.user_name, "text": c.text, "created_at": c.created_at.isoformat()} for c in comments]
        })
    return result


@router.post("/posts", status_code=status.HTTP_201_CREATED)
def create_friend_search_post(
    college: str = Form(...),
    batch: Optional[str] = Form(None),
    message: str = Form(...),
    title: str = Form(""),
    category: str = Form("friend"),
    privacy: str = Form("public"),
    anonymous: bool = Form(False),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new Friend Search post."""
    
    photo_url = None
    
    if photo and hasattr(photo, 'filename') and photo.filename:
        try:
            photo_url = save_photo(photo)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Photo upload failed: {str(e)}")

    new_post = SocialPost(
        user_id=current_user.id,
        user_name=current_user.full_name,
        college=college,  # ✅ Use the college provided (e.g., "RV College of Engineering")
        batch=batch,
        message=message,
        title=title,
        category="friend",  # ✅ Force category to "friend"
        photo=photo_url,
        video_url=None,
        privacy=privacy,
        anonymous=anonymous,
        likes_count=0
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    return {"success": True, "id": new_post.id, "photo": photo_url}


@router.post("/posts/{post_id}/like")
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Like or unlike a Friend Search post"""
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.college == "Mood & Memory":
        raise HTTPException(status_code=400, detail="Not a Friend Search post")

    existing_like = db.query(SocialLike).filter(
        SocialLike.post_id == post_id,
        SocialLike.user_id == current_user.id
    ).first()
    if existing_like:
        db.delete(existing_like)
        post.likes_count -= 1
        db.commit()
        return {"liked": False, "likes_count": post.likes_count}
    else:
        new_like = SocialLike(post_id=post_id, user_id=current_user.id)
        db.add(new_like)
        post.likes_count += 1
        db.commit()
        return {"liked": True, "likes_count": post.likes_count}


@router.post("/posts/{post_id}/comment")
def add_comment(
    post_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a comment to a Friend Search post"""
    text = data.get("text")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.college == "Mood & Memory":
        raise HTTPException(status_code=400, detail="Not a Friend Search post")

    comment = SocialComment(
        post_id=post_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        text=text.strip()
    )
    db.add(comment)
    db.commit()
    return {"success": True, "comment_id": comment.id}


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a Friend Search post (only author can delete)"""
    post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.college == "Mood & Memory":
        raise HTTPException(status_code=400, detail="Not a Friend Search post")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    db.delete(post)
    db.commit()
    return {"success": True}