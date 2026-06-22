from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User, ConnectionRequest
from app.auth import get_current_user

router = APIRouter(prefix="/api/connections", tags=["Connections"])

class ConnectionRequestCreate(BaseModel):
    to_user_id: int
    post_id: Optional[int] = None   # optional, to link to a post

class ConnectionRequestResponse(BaseModel):
    id: int
    from_user_id: int
    from_user_name: str
    to_user_id: int
    status: str
    created_at: datetime
    responded_at: Optional[datetime]

class ConnectionAccept(BaseModel):
    accept: bool   # true = accept, false = reject

@router.post("/request")
def send_connection_request(
    req: ConnectionRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a connection request from current_user to to_user_id"""
    if current_user.id == req.to_user_id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")

    existing = db.query(ConnectionRequest).filter(
        ((ConnectionRequest.from_user_id == current_user.id) & (ConnectionRequest.to_user_id == req.to_user_id)) |
        ((ConnectionRequest.from_user_id == req.to_user_id) & (ConnectionRequest.to_user_id == current_user.id))
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Request already exists")

    new_req = ConnectionRequest(
        from_user_id=current_user.id,
        to_user_id=req.to_user_id,
        status="pending"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return {"success": True, "request_id": new_req.id}

@router.get("/incoming", response_model=List[ConnectionRequestResponse])
def get_incoming_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pending requests sent to current_user"""
    requests = db.query(ConnectionRequest).filter(
        ConnectionRequest.to_user_id == current_user.id,
        ConnectionRequest.status == "pending"
    ).order_by(ConnectionRequest.created_at.desc()).all()
    result = []
    for r in requests:
        from_user = db.query(User).filter(User.id == r.from_user_id).first()
        result.append({
            "id": r.id,
            "from_user_id": r.from_user_id,
            "from_user_name": from_user.full_name if from_user else "Unknown",
            "to_user_id": r.to_user_id,
            "status": r.status,
            "created_at": r.created_at,
            "responded_at": r.responded_at
        })
    return result

@router.post("/respond/{request_id}")
def respond_to_request(
    request_id: int,
    data: ConnectionAccept,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept or reject a connection request"""
    conn_req = db.query(ConnectionRequest).filter(
        ConnectionRequest.id == request_id,
        ConnectionRequest.to_user_id == current_user.id
    ).first()
    if not conn_req:
        raise HTTPException(status_code=404, detail="Request not found")

    if data.accept:
        conn_req.status = "accepted"
    else:
        conn_req.status = "rejected"
    conn_req.responded_at = datetime.utcnow()
    db.commit()
    return {"success": True, "status": conn_req.status}

@router.get("/accepted", response_model=List[dict])
def get_accepted_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all accepted connections with contact info"""
    requests = db.query(ConnectionRequest).filter(
        ((ConnectionRequest.from_user_id == current_user.id) | (ConnectionRequest.to_user_id == current_user.id)),
        ConnectionRequest.status == "accepted"
    ).all()
    result = []
    for r in requests:
        other_id = r.from_user_id if r.to_user_id == current_user.id else r.to_user_id
        other_user = db.query(User).filter(User.id == other_id).first()
        if other_user:
            # Expose mobile number (whatsapp) – you can also expose email
            contact = other_user.whatsapp
            result.append({
                "user_id": other_user.id,
                "full_name": other_user.full_name,
                "college": other_user.college,
                "contact": contact
            })
    return result