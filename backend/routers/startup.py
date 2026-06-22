from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/startup", tags=["Ants' Startup Nest"])

# ============ MODELS ============
class StartupIdeaCreate(BaseModel):
    title: str
    category: str
    pitch: str
    description: Optional[str] = None
    looking_for: str
    whatsapp: Optional[str] = None

class StartupIdeaResponse(BaseModel):
    id: int
    title: str
    category: str
    pitch: str
    description: Optional[str]
    looking_for: str
    founder_name: str
    college: str
    whatsapp: Optional[str]
    created_at: str
    interest_count: int

class InterestRequest(BaseModel):
    idea_id: int
    message: Optional[str] = None


# In-memory storage
ideas_db = []
ideas_counter = 0
interests_db = []


@router.post("/create", response_model=dict)
def create_startup_idea(
    data: StartupIdeaCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post a startup idea"""
    global ideas_counter
    ideas_counter += 1
    
    ideas_db.append({
        "id": ideas_counter,
        "user_id": current_user.id,
        "title": data.title,
        "category": data.category,
        "pitch": data.pitch,
        "description": data.description,
        "looking_for": data.looking_for,
        "founder_name": current_user.full_name,
        "college": getattr(current_user, "college", None),
        "whatsapp": data.whatsapp,
        "created_at": datetime.now().isoformat(),
        "interest_count": 0,
        "is_active": True
    })
    
    return {"success": True, "id": ideas_counter, "message": "Idea posted successfully"}


@router.get("/list", response_model=List[StartupIdeaResponse])
def list_startup_ideas(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get all startup ideas"""
    
    results = [i for i in ideas_db if i.get("is_active", True)]
    
    if category and category != "all":
        results = [i for i in results if i["category"] == category]
    
    results.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [
        StartupIdeaResponse(
            id=i["id"],
            title=i["title"],
            category=i["category"],
            pitch=i["pitch"],
            description=i.get("description"),
            looking_for=i["looking_for"],
            founder_name=i["founder_name"],
            college=i.get("college") or "Not specified",
            whatsapp=i.get("whatsapp"),
            created_at=i["created_at"],
            interest_count=i.get("interest_count", 0)
        )
        for i in results
    ]


@router.post("/interest")
def express_interest(
    request: InterestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Express interest in a startup idea"""
    
    # ========== NEW VALIDATION (fix for missing message) ==========
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=422,
            detail="Message is required to express interest"
        )
    # ==============================================================
    
    idea = next((i for i in ideas_db if i["id"] == request.idea_id), None)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    existing = next((i for i in interests_db 
                     if i["idea_id"] == request.idea_id and i["user_id"] == current_user.id), None)
    
    if not existing:
        interests_db.append({
            "idea_id": request.idea_id,
            "user_id": current_user.id,
            "message": request.message,
            "created_at": datetime.now().isoformat()
        })
        idea["interest_count"] = idea.get("interest_count", 0) + 1
    
    return {
        "success": True,
        "message": f"Interest recorded for {idea['title']}",
        "founder_whatsapp": idea.get("whatsapp")
    }