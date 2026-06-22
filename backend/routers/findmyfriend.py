"""
FIND MY FRIEND – NON‑AI VERSION (Keyword Search Only)
================================================================================
This module helps users reconnect with lost friends using:
- Story submission with optional hint questions
- Contact info hidden behind correct answers to hints
- Keyword search (college, batch, names, story text)

All AI / embedding code has been removed. The search endpoint uses simple
keyword matching on story text and extracted metadata.

Endpoints:
    POST   /api/findmyfriend/create        - Submit a new story
    GET    /api/findmyfriend/search        - Keyword search for stories
    POST   /api/findmyfriend/reveal/{id}   - Reveal contact after answering hints
    GET    /api/findmyfriend/my-stories    - Get current user's stories
    DELETE /api/findmyfriend/delete/{id}   - Delete a story (owner only)
"""

import json
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import User, FriendStory
from app.schemas import (
    FriendStoryCreate,
    FriendStoryResponse,
    FriendStoryRevealRequest,
    FriendStoryRevealResponse
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/findmyfriend", tags=["Find My Friend"])


# ============ HELPER FUNCTIONS ============

def extract_metadata_from_story(story_text: str) -> dict:
    """
    Extract names, colleges, batches, and nicknames from story text using regex.
    Used for keyword search indexing and display.
    """
    text_lower = story_text.lower()
    
    # Extract potential names (capitalized words or quoted names)
    name_pattern = r'(?:friend|classmate|batchmate|colleague|name(?:d)?|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
    names = re.findall(name_pattern, story_text)
    
    # Extract colleges (common Karnataka college names)
    colleges_list = [
        "RVCE", "PES", "BMS", "NITK", "UBDTCE", "KLEIT", "Manipal", "Christ",
        "RV College", "PES University", "BMS College", "NITK Surathkal",
        "UBDT College", "KLE Institute", "SDM", "MITE", "Sahyadri", "NMAMIT"
    ]
    colleges = [c for c in colleges_list if c.lower() in text_lower]
    
    # Extract batch years (4-digit years from 1990-2030)
    batch_pattern = r'\b(19[8-9][0-9]|20[0-2][0-9]|2030)\b'
    batches = re.findall(batch_pattern, story_text)
    
    # Extract nicknames (anything in quotes or after "nickname")
    nickname_pattern = r'nickname(?:d)?\s+(?:["\'])?([A-Za-z0-9]+)(?:["\'])?'
    nicknames = re.findall(nickname_pattern, text_lower)
    
    return {
        "extracted_names": ", ".join(set(names[:10])),
        "extracted_colleges": ", ".join(set(colleges[:5])),
        "extracted_batches": ", ".join(set(batches[:5])),
        "extracted_nicknames": ", ".join(set(nicknames[:5]))
    }


def compute_keyword_score(story: FriendStory, query: str) -> float:
    """
    Compute a relevance score (0‑100) based on how many query terms match
    the story text, extracted names, colleges, batches, or nicknames.
    """
    query_lower = query.lower()
    score = 0.0
    
    # Direct match in story text
    if story.story_text.lower().find(query_lower) != -1:
        score += 40
    
    # Extracted names
    if story.extracted_names:
        for name in story.extracted_names.split(','):
            if name.strip().lower() in query_lower:
                score += 15
                break
    
    # Extracted colleges
    if story.extracted_colleges:
        for college in story.extracted_colleges.split(','):
            if college.strip().lower() in query_lower:
                score += 15
                break
    
    # Extracted batches
    if story.extracted_batches:
        for batch in story.extracted_batches.split(','):
            if batch.strip() in query_lower:
                score += 15
                break
    
    # Extracted nicknames
    if story.extracted_nicknames:
        for nick in story.extracted_nicknames.split(','):
            if nick.strip().lower() in query_lower:
                score += 15
                break
    
    return min(score, 100.0)


# ============ CREATE STORY ============

@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_friend_story(
    story_data: FriendStoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a new story about someone you're looking for.
    """
    # Validations
    if not story_data.story_text or not story_data.story_text.strip():
        raise HTTPException(
            status_code=400,
            detail="story_text is required and cannot be empty"
        )
    
    if not story_data.contact_email and not story_data.contact_mobile:
        raise HTTPException(
            status_code=400,
            detail="At least one contact method (email or mobile) is required"
        )
    
    if story_data.contact_email:
        if "@" not in story_data.contact_email or "." not in story_data.contact_email.split("@")[-1]:
            raise HTTPException(
                status_code=400,
                detail="Invalid email format"
            )
    
    if story_data.hint_questions and len(story_data.hint_questions) > 0:
        if not story_data.contact_email and not story_data.contact_mobile:
            raise HTTPException(
                status_code=400,
                detail="You must provide at least one contact method when using hint questions"
            )
    
    # Extract metadata
    metadata = extract_metadata_from_story(story_data.story_text)
    
    # Store hint questions as JSON
    hints_json = json.dumps(story_data.hint_questions) if story_data.hint_questions else None
    
    new_story = FriendStory(
        user_id=current_user.id,
        story_text=story_data.story_text,
        story_embedding=None,           # No AI embeddings
        contact_email=story_data.contact_email,
        contact_mobile=story_data.contact_mobile,
        hint_questions=hints_json,
        extracted_names=metadata["extracted_names"],
        extracted_colleges=metadata["extracted_colleges"],
        extracted_batches=metadata["extracted_batches"],
        extracted_nicknames=metadata["extracted_nicknames"],
        is_active=True
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return {
        "success": True,
        "story_id": new_story.id,
        "message": "Your story has been posted.",
        "extracted_metadata": metadata
    }


# ============ GET MY STORIES ============

@router.get("/my-stories", response_model=List[FriendStoryResponse])
def get_my_stories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """Get all stories posted by the current user."""
    stories = db.query(FriendStory).filter(
        FriendStory.user_id == current_user.id,
        FriendStory.is_active == True
    ).order_by(desc(FriendStory.created_at)).limit(limit).all()
    
    result = []
    for story in stories:
        hints = None
        if story.hint_questions:
            try:
                hints_list = json.loads(story.hint_questions)
                hints = [{"question": h.get("question", "")} for h in hints_list]
            except:
                hints = None
        
        result.append(FriendStoryResponse(
            id=story.id,
            user_id=story.user_id,
            user_name=current_user.full_name,
            story_text=story.story_text,
            extracted_names=story.extracted_names,
            extracted_colleges=story.extracted_colleges,
            extracted_batches=story.extracted_batches,
            extracted_nicknames=story.extracted_nicknames,
            hint_questions=hints,
            created_at=story.created_at
        ))
    return result


# ============ DELETE STORY ============

@router.delete("/delete/{story_id}", response_model=dict)
def delete_friend_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a story (soft delete)."""
    story = db.query(FriendStory).filter(FriendStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own stories")
    
    story.is_active = False
    db.commit()
    return {"success": True, "message": "Story deleted successfully"}


# ============ SEARCH STORIES (Keyword Only) ============

@router.get("/search", response_model=List[FriendStoryResponse])
def search_friend_stories(
    q: str = Query(..., min_length=1, description="Search query (e.g., 'Priya from RVCE 2019 batch')"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Search for stories using keyword matching (no AI).
    """
    stories = db.query(FriendStory).filter(FriendStory.is_active == True).all()
    if not stories:
        return []
    
    results = []
    for story in stories:
        score = compute_keyword_score(story, q)
        if score >= 20:   # threshold
            hints = None
            if story.hint_questions:
                try:
                    hints_list = json.loads(story.hint_questions)
                    hints = [{"question": h.get("question", "")} for h in hints_list]
                except:
                    hints = None
            
            user = db.query(User).filter(User.id == story.user_id).first()
            user_name = user.full_name if user else "Anonymous"
            
            results.append(FriendStoryResponse(
                id=story.id,
                user_id=story.user_id,
                user_name=user_name,
                story_text=story.story_text,
                extracted_names=story.extracted_names,
                extracted_colleges=story.extracted_colleges,
                extracted_batches=story.extracted_batches,
                extracted_nicknames=story.extracted_nicknames,
                hint_questions=hints,
                created_at=story.created_at,
                match_score=score
            ))
    
    results.sort(key=lambda x: x.match_score or 0, reverse=True)
    return results[:limit]


# ============ REVEAL CONTACT INFO ============

@router.post("/reveal/{story_id}", response_model=FriendStoryRevealResponse)
def reveal_contact_info(
    story_id: int,
    reveal_request: FriendStoryRevealRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reveal contact information after correctly answering hint questions.
    """
    story = db.query(FriendStory).filter(
        FriendStory.id == story_id,
        FriendStory.is_active == True
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot request contact info for your own story"
        )
    
    if not story.hint_questions:
        return FriendStoryRevealResponse(
            success=True,
            contact_email=story.contact_email,
            contact_mobile=story.contact_mobile,
            message="Contact information revealed successfully."
        )
    
    try:
        stored_hints = json.loads(story.hint_questions)
    except:
        raise HTTPException(status_code=500, detail="Invalid hint data stored")
    
    if len(reveal_request.answers) != len(stored_hints):
        raise HTTPException(
            status_code=400,
            detail=f"Please provide answers for all {len(stored_hints)} hint questions"
        )
    
    all_correct = True
    for i, hint in enumerate(stored_hints):
        stored_answer = hint.get("answer", "").strip().lower()
        provided_answer = reveal_request.answers[i].strip().lower()
        if stored_answer != provided_answer:
            all_correct = False
            break
    
    if not all_correct:
        raise HTTPException(
            status_code=403,
            detail="One or more answers were incorrect. Cannot reveal contact information."
        )
    
    story.contact_revealed_count = (story.contact_revealed_count or 0) + 1
    db.commit()
    
    return FriendStoryRevealResponse(
        success=True,
        contact_email=story.contact_email,
        contact_mobile=story.contact_mobile,
        message="Contact information revealed successfully. Please be respectful when reaching out."
    )