from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/business", tags=["Family Business Showcase"])

# ============ MODELS ============
class BusinessCreate(BaseModel):
    name: str
    category: str
    location: str
    whatsapp: str
    description: Optional[str] = None
    student_name: str
    college: str

class BusinessResponse(BaseModel):
    id: int
    name: str
    category: str
    location: str
    whatsapp: str
    description: Optional[str]
    student_name: str
    college: str
    created_at: str
    views: int

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


# In-memory storage (replace with database table)
business_db = []
business_counter = 0

@router.post("/create", response_model=dict)
def create_business(
    data: BusinessCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List a family business"""
    global business_counter
    business_counter += 1
    
    business_db.append({
        "id": business_counter,
        "user_id": current_user.id,
        "name": data.name,
        "category": data.category,
        "location": data.location,
        "whatsapp": data.whatsapp,
        "description": data.description,
        "student_name": data.student_name,
        "college": data.college,
        "created_at": datetime.now().isoformat(),
        "views": 0,
        "is_active": True
    })
    
    return {"success": True, "id": business_counter, "message": "Business listed successfully"}


@router.get("/list", response_model=List[BusinessResponse])
def list_businesses(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or location"),
    db: Session = Depends(get_db)
):
    """Get all listed family businesses"""
    
    results = [b for b in business_db if b.get("is_active", True)]
    
    if category and category != "all":
        results = [b for b in results if b["category"] == category]
    
    if search:
        search_lower = search.lower()
        results = [b for b in results 
                   if search_lower in b["name"].lower() 
                   or search_lower in b["location"].lower()]
    
    # Increment view count for API call (simplified)
    for r in results:
        r["views"] += 1
    
    return [
        BusinessResponse(
            id=b["id"],
            name=b["name"],
            category=b["category"],
            location=b["location"],
            whatsapp=b["whatsapp"],
            description=b.get("description"),
            student_name=b["student_name"],
            college=b["college"],
            created_at=b["created_at"],
            views=b.get("views", 0)
        )
        for b in results
    ]


@router.delete("/{business_id}")
def delete_business(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a business listing (only creator or admin)"""
    
    business = next((b for b in business_db if b["id"] == business_id), None)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if business["user_id"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    business["is_active"] = False
    
    return {"success": True, "message": "Business deleted"}