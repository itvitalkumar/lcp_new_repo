from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/hive", tags=["Keep the Hive Buzzing"])

# ============ MODELS ============
class ContributionRequest(BaseModel):
    amount: int
    message: Optional[str] = None

class ContributionResponse(BaseModel):
    id: int
    user_name: str
    amount: int
    message: Optional[str]
    created_at: str

class HiveStatsResponse(BaseModel):
    total_businesses_helped: int
    total_contributions: int
    active_campaigns: int
    recent_contributions: List[ContributionResponse]

class TestimonialCreate(BaseModel):
    story: str
    author: str
    business_name: Optional[str] = None


# In-memory storage
contributions_db = []
contributions_counter = 0
testimonials_db = []

# Default stats
stats = {
    "total_businesses_helped": 23,
    "total_contributions": 5470,
    "active_campaigns": 8
}

@router.post("/contribute", response_model=dict)
def record_contribution(
    data: ContributionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a voluntary contribution"""
    global contributions_counter
    contributions_counter += 1
    
    contributions_db.append({
        "id": contributions_counter,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "amount": data.amount,
        "message": data.message,
        "created_at": datetime.now().isoformat()
    })
    
    # Update stats
    stats["total_contributions"] += data.amount
    stats["total_businesses_helped"] += max(1, data.amount // 10)
    
    return {
        "success": True,
        "message": f"Thank you for contributing ₹{data.amount}!",
        "businesses_helped": data.amount // 10
    }


@router.get("/stats", response_model=HiveStatsResponse)
def get_hive_stats(
    db: Session = Depends(get_db)
):
    """Get hive statistics"""
    
    return HiveStatsResponse(
        total_businesses_helped=stats["total_businesses_helped"],
        total_contributions=stats["total_contributions"],
        active_campaigns=stats["active_campaigns"],
        recent_contributions=[
            ContributionResponse(
                id=c["id"],
                user_name=c["user_name"],
                amount=c["amount"],
                message=c.get("message"),
                created_at=c["created_at"]
            )
            for c in contributions_db[-5:]  # Last 5 contributions
        ]
    )


@router.post("/testimonial")
def add_testimonial(
    data: TestimonialCreate,
    db: Session = Depends(get_db)
):
    """Add a success testimonial"""
    
    testimonials_db.append({
        "story": data.story,
        "author": data.author,
        "business_name": data.business_name,
        "created_at": datetime.now().isoformat()
    })
    
    return {"success": True, "message": "Testimonial added"}


@router.get("/testimonials")
def get_testimonials():
    """Get all testimonials"""
    
    return testimonials_db