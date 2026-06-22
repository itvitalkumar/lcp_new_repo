from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import SuccessStory
from app.schemas import StoryCreate, StoryResponse
from app.auth import get_current_active_user, get_current_admin

router = APIRouter(prefix="/api/stories", tags=["Success Stories"])


# ============ CREATE STORY (Main endpoint) ============
@router.post("/", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(
    story_data: StoryCreate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new success story (requires authentication)"""
    
    new_story = SuccessStory(
        story_text=story_data.story_text,
        author_name=story_data.author_name,
        is_approved=False
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return StoryResponse(
        id=new_story.id,
        story_text=new_story.story_text,
        author_name=new_story.author_name,
        created_at=new_story.created_at
    )


# ============ NEW: CREATE STORY ALIAS (for frontend compatibility) ============
@router.post("/create", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
def create_story_alias(
    story_data: StoryCreate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Alias for /api/stories/ - creates a new success story"""
    
    new_story = SuccessStory(
        story_text=story_data.story_text,
        author_name=story_data.author_name,
        is_approved=False
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return StoryResponse(
        id=new_story.id,
        story_text=new_story.story_text,
        author_name=new_story.author_name,
        created_at=new_story.created_at
    )


# ============ GET ALL STORIES (Approved only by default) ============
@router.get("/", response_model=List[StoryResponse])
def get_stories(
    approved_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all success stories (approved stories by default)"""
    
    query = db.query(SuccessStory)
    
    if approved_only:
        query = query.filter(SuccessStory.is_approved == True)
    
    stories = query.order_by(SuccessStory.created_at.desc()).all()
    
    return [
        StoryResponse(
            id=s.id,
            story_text=s.story_text,
            author_name=s.author_name,
            created_at=s.created_at
        )
        for s in stories
    ]


# ============ GET PENDING STORIES (Admin only) ============
@router.get("/pending", response_model=List[StoryResponse])
def get_pending_stories(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get stories pending approval (admin only)"""
    
    stories = db.query(SuccessStory).filter(
        SuccessStory.is_approved == False
    ).order_by(SuccessStory.created_at.desc()).all()
    
    return [
        StoryResponse(
            id=s.id,
            story_text=s.story_text,
            author_name=s.author_name,
            created_at=s.created_at
        )
        for s in stories
    ]


# ============ APPROVE STORY (Admin only) ============
@router.put("/{story_id}/approve")
def approve_story(
    story_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve a success story (admin only)"""
    
    story = db.query(SuccessStory).filter(SuccessStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story.is_approved = True
    db.commit()
    
    return {"success": True, "message": "Story approved successfully"}


# ============ DELETE STORY (Admin only) ============
@router.delete("/{story_id}")
def delete_story(
    story_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a success story (admin only)"""
    
    story = db.query(SuccessStory).filter(SuccessStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    db.delete(story)
    db.commit()
    
    return {"success": True, "message": "Story deleted successfully"}