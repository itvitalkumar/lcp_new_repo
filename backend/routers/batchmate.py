from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/batchmate", tags=["Batchmate Finder"])

# ============ MODELS ============
class BatchmateRegister(BaseModel):
    name: str
    college: str
    batch: str
    whatsapp: Optional[str] = None

class BatchmateSearch(BaseModel):
    college: str
    batch: str

class BatchmateResponse(BaseModel):
    id: int
    name: str
    college: str
    batch: str
    consent: bool
    match_score: Optional[int] = None

class ConnectRequest(BaseModel):
    target_user_id: int
    message: str


# In-memory storage for demo (replace with database table in production)
batchmate_db = []

@router.post("/register")
def register_batchmate(
    data: BatchmateRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register yourself as a batchmate seeker"""
    
    # Check if already registered
    existing = next((b for b in batchmate_db if b["user_id"] == current_user.id), None)
    if existing:
        existing["name"] = data.name
        existing["college"] = data.college
        existing["batch"] = data.batch
        existing["whatsapp"] = data.whatsapp
        existing["updated_at"] = datetime.now().isoformat()
        return {"success": True, "message": "Profile updated"}
    
    batchmate_db.append({
        "id": len(batchmate_db) + 1,
        "user_id": current_user.id,
        "name": data.name,
        "college": data.college,
        "batch": data.batch,
        "whatsapp": data.whatsapp,
        "consent": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })
    
    return {"success": True, "message": "Registered successfully"}


@router.get("/search", response_model=List[BatchmateResponse])
def search_batchmates(
    college: str,
    batch: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Find batchmates from same college and batch"""
    
    matches = [b for b in batchmate_db 
               if b["college"].lower() == college.lower() 
               and b["batch"] == batch
               and b["user_id"] != current_user.id]
    
    # Simple fuzzy matching for name similarity
    current_name = next((b["name"] for b in batchmate_db if b["user_id"] == current_user.id), "")
    
    results = []
    for match in matches:
        # Calculate simple match score
        score = 85
        if current_name and match["name"]:
            # Simple name similarity
            if current_name.lower() in match["name"].lower() or match["name"].lower() in current_name.lower():
                score = 95
        
        results.append(BatchmateResponse(
            id=match["id"],
            name=match["name"],
            college=match["college"],
            batch=match["batch"],
            consent=match["consent"],
            match_score=score
        ))
    
    return results


@router.post("/connect")
def request_connection(
    request: ConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request contact with a batchmate"""
    
    target = next((b for b in batchmate_db if b["id"] == request.target_user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Batchmate not found")
    
    # In production, store in database and send notification
    return {
        "success": True,
        "message": f"Connection request sent to {target['name']}",
        "target_whatsapp": target.get("whatsapp")
    }