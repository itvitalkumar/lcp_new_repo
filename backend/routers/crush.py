from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import random

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/crush", tags=["Crush Corner"])

# ============ MODELS ============
class QuizSubmit(BaseModel):
    your_name: str
    crush_name: str
    answers: List[int]  # 5 answers (1-5 scale)
    user_id: Optional[int] = None

class QuizResponse(BaseModel):
    id: int
    your_name: str
    crush_name: str
    compatibility_score: int
    message: str
    created_at: str

class NameGenerateRequest(BaseModel):
    your_name: str
    partner_name: str
    user_id: Optional[int] = None

class NameResponse(BaseModel):
    id: int
    your_name: str
    partner_name: str
    couple_name: str
    votes: int
    created_at: str


# In-memory storage (replace with database tables)
quiz_results_db = []
quiz_counter = 0
name_results_db = []
name_counter = 0
avatar_creations_db = []
avatar_counter = 0

# Quiz compatibility calculation
def calculate_compatibility(answers: List[int]) -> dict:
    """Calculate compatibility score based on answers"""
    total = sum(answers)
    max_possible = 25  # 5 questions * 5 max
    raw_score = (total / max_possible) * 100
    
    # Add some random factor for fun (±10%)
    random_factor = random.randint(-10, 10)
    score = min(99, max(30, int(raw_score + random_factor)))
    
    if score >= 85:
        message = "💖 Amazing compatibility! You two are a perfect match! The stars align in your favor. Keep building that connection! ✨"
    elif score >= 70:
        message = "💛 Great potential! You share good chemistry. With a little effort, this could turn into something beautiful! 🌟"
    elif score >= 55:
        message = "💚 Good friends first! You have a solid foundation. Take your time and let things grow naturally. 🌱"
    elif score >= 40:
        message = "💙 Interesting combination! You complement each other in unexpected ways. Give it a chance! 🦋"
    else:
        message = "💜 Opposites attract! You might be very different, but that can be a good thing. Explore the connection! 🌈"
    
    return {"score": score, "message": message}


@router.post("/quiz/submit", response_model=dict)
def submit_quiz(
    data: QuizSubmit,
    db: Session = Depends(get_db)
):
    """Submit quiz answers and get compatibility score"""
    global quiz_counter
    quiz_counter += 1
    
    # Calculate compatibility
    result = calculate_compatibility(data.answers)
    
    # Store in database
    quiz_results_db.append({
        "id": quiz_counter,
        "your_name": data.your_name,
        "crush_name": data.crush_name,
        "answers": data.answers,
        "compatibility_score": result["score"],
        "message": result["message"],
        "user_id": data.user_id,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "id": quiz_counter,
        "compatibility_score": result["score"],
        "message": result["message"],
        "your_name": data.your_name,
        "crush_name": data.crush_name
    }


@router.get("/quiz/leaderboard", response_model=List[QuizResponse])
def get_leaderboard(
    limit: int = Query(10, description="Number of top results"),
    db: Session = Depends(get_db)
):
    """Get top compatibility scores"""
    
    sorted_results = sorted(quiz_results_db, key=lambda x: x["compatibility_score"], reverse=True)
    top_results = sorted_results[:limit]
    
    return [
        QuizResponse(
            id=r["id"],
            your_name=r["your_name"],
            crush_name=r["crush_name"],
            compatibility_score=r["compatibility_score"],
            message=r["message"],
            created_at=r["created_at"]
        )
        for r in top_results
    ]


@router.get("/quiz/stats")
def get_quiz_stats(db: Session = Depends(get_db)):
    """Get quiz statistics"""
    
    if not quiz_results_db:
        return {"total_attempts": 0, "average_score": 0}
    
    total_score = sum(r["compatibility_score"] for r in quiz_results_db)
    avg_score = total_score / len(quiz_results_db)
    
    return {
        "total_attempts": len(quiz_results_db),
        "average_score": round(avg_score, 1),
        "highest_score": max(r["compatibility_score"] for r in quiz_results_db)
    }


@router.post("/name/generate", response_model=dict)
def generate_couple_name(
    data: NameGenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate and store a unique couple name"""
    global name_counter
    name_counter += 1
    
    # ========== FIX: Prevent empty names (crash fix) ==========
    your_name = data.your_name.strip() if data.your_name else ""
    partner_name = data.partner_name.strip() if data.partner_name else ""
    
    if not your_name or not partner_name:
        raise HTTPException(
            status_code=400,
            detail="Both your_name and partner_name are required and cannot be empty"
        )
    # ==========================================================
    
    # Generate couple name
    name1 = your_name.lower().replace(" ", "")
    name2 = partner_name.lower().replace(" ", "")
    
    # Different name styles
    styles = [
        f"{name1[:3]}{name2[-3:]}".capitalize(),
        f"{name1[:4]}❤️{name2[:4]}".capitalize(),
        f"{name1[0].upper()}{name2[:3]}{name1[-2:]}".capitalize(),
        f"{name1[:2]}{name2[:2]}{name1[-2]}".capitalize(),
        f"{name1[:3]}{name2[:3]}".capitalize()
    ]
    
    style_index = (len(name1) + len(name2)) % len(styles)
    couple_name = styles[style_index]
    
    # Add fun suffix
    suffixes = ["💕", "✨", "💖", "🌸", "⭐", "💫", "🌈"]
    suffix_index = len(couple_name) % len(suffixes)
    full_name = f"{couple_name} {suffixes[suffix_index]}"
    
    # Store
    name_results_db.append({
        "id": name_counter,
        "your_name": your_name,
        "partner_name": partner_name,
        "couple_name": full_name,
        "votes": 0,
        "user_id": data.user_id,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "success": True,
        "id": name_counter,
        "couple_name": full_name,
        "your_name": your_name,
        "partner_name": partner_name
    }


@router.get("/name/trending", response_model=List[NameResponse])
def get_trending_names(
    limit: int = Query(10, description="Number of trending names"),
    db: Session = Depends(get_db)
):
    """Get most popular generated couple names"""
    
    sorted_names = sorted(name_results_db, key=lambda x: x["votes"], reverse=True)
    top_names = sorted_names[:limit]
    
    return [
        NameResponse(
            id=n["id"],
            your_name=n["your_name"],
            partner_name=n["partner_name"],
            couple_name=n["couple_name"],
            votes=n["votes"],
            created_at=n["created_at"]
        )
        for n in top_names
    ]


@router.post("/name/vote/{name_id}")
def vote_couple_name(
    name_id: int,
    db: Session = Depends(get_db)
):
    """Vote for a couple name (increment vote count)"""
    
    for name in name_results_db:
        if name["id"] == name_id:
            name["votes"] += 1
            return {"success": True, "votes": name["votes"]}
    
    raise HTTPException(status_code=404, detail="Name not found")