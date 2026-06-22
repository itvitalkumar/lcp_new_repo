from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/search")
def search_users(
    name: Optional[str] = Query(None),
    college: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(User)
    if name:
        query = query.filter(User.full_name.ilike(f"%{name}%"))
    if college:
        query = query.filter(User.college.ilike(f"%{college}%"))
    # batch is not a column in your User model – ignore for now
    users = query.limit(50).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "college": u.college,
        }
        for u in users
    ]