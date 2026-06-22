# routers/messages.py - Complete Chat System for Campus Central
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import base64
import uuid
import os

from pydantic import BaseModel

from app.database import get_db
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember, Message
from app.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/messages", tags=["Messages"])


# ============ SCHEMAS ============
class MessageSend(BaseModel):
    group_id: str
    group_type: str
    message: str
    image: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    message: str
    image_url: Optional[str]
    created_at: str


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int


# ============ HELPER: Save Image ============
def save_image(base64_string: str) -> Optional[str]:
    """Save base64 image to disk and return URL"""
    if not base64_string:
        return None
    
    try:
        if base64_string.startswith("data:image"):
            base64_string = base64_string.split(",")[1]
        
        image_data = base64.b64decode(base64_string)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        filename = f"chat_img_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return f"/uploads/{filename}"
    except Exception as e:
        print(f"Error saving image: {e}")
        return None
    # ============ 1. SEND MESSAGE ============
@router.post("/send", response_model=dict)
def send_message(
    data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a group - text or image"""
    
    # ========== FIX: Reject empty or whitespace‑only messages ==========
    if not data.message or not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    # ==================================================================
    
    print(f"💬 MESSAGE - Group: {data.group_id}, Type: {data.group_type}, User: {current_user.id}")
    
    # Find the group
    group_db_id = None
    if data.group_type == "teacher":
        group = db.query(TeacherGroup).filter(TeacherGroup.group_id == data.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Teacher group not found")
        group_db_id = group.id
    elif data.group_type == "celebration":
        group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == data.group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Celebration group not found")
        group_db_id = group.id
    else:
        raise HTTPException(status_code=400, detail="Invalid group_type")
    
    # Check if user is a member
    is_member = False
    if data.group_type == "teacher":
        member = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group_db_id,
            GroupMember.user_id == current_user.id
        ).first()
        is_member = member is not None
    else:
        member = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == group_db_id,
            GroupMember.user_id == current_user.id
        ).first()
        is_member = member is not None
    
    if not is_member:
        print(f"❌ User {current_user.id} is NOT a member")
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    
    # Save image if provided
    image_url = save_image(data.image) if data.image else None
    
    # Create message
    final_message = data.message
    if image_url:
        final_message = f"[IMAGE] {data.message}" if data.message else "[IMAGE]"
    
    new_message = Message(
        group_type=data.group_type,
        teacher_group_id=group_db_id if data.group_type == "teacher" else None,
        celebration_group_id=group_db_id if data.group_type == "celebration" else None,
        user_id=current_user.id,
        message=final_message,
        sent_at=datetime.utcnow()
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    print(f"✅ Message {new_message.id} saved")
    
    return {
        "success": True,
        "message_id": new_message.id,
        "message": data.message,
        "image_url": image_url,
        "sent_at": new_message.sent_at.isoformat()
    }


# ============ 2. GET MESSAGES ============
@router.get("/{group_id}")
def get_messages(
    group_id: str,
    group_type: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a group"""
    
    # Find the group
    group_db_id = None
    if group_type == "teacher":
        group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Teacher group not found")
        group_db_id = group.id
    elif group_type == "celebration":
        group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Celebration group not found")
        group_db_id = group.id
    else:
        raise HTTPException(status_code=400, detail="Invalid group_type")
    
    # Check membership
    is_member = False
    if group_type == "teacher":
        member = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group_db_id,
            GroupMember.user_id == current_user.id
        ).first()
        is_member = member is not None
    else:
        member = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == group_db_id,
            GroupMember.user_id == current_user.id
        ).first()
        is_member = member is not None
    
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member")
    
    # Get messages
    if group_type == "teacher":
        messages = db.query(Message).filter(
            Message.teacher_group_id == group_db_id,
            Message.group_type == "teacher"
        ).order_by(Message.sent_at.desc()).limit(limit).all()
    else:
        messages = db.query(Message).filter(
            Message.celebration_group_id == group_db_id,
            Message.group_type == "celebration"
        ).order_by(Message.sent_at.desc()).limit(limit).all()
    
    messages.reverse()
    
    result = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.user_id).first()
        
        # Extract image from message if present
        image_url = None
        message_text = msg.message
        if msg.message and msg.message.startswith("[IMAGE]"):
            image_url = "/uploads/placeholder.jpg"
            message_text = msg.message.replace("[IMAGE]", "").strip()
        
        result.append({
            "id": msg.id,
            "sender_id": msg.user_id,
            "sender_name": sender.full_name if sender else "Unknown",
            "message": message_text,
            "image_url": image_url,
            "created_at": msg.sent_at.isoformat()
        })
    
    return {"messages": result, "total": len(result)}


# ============ 3. DELETE MESSAGE ============
@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a message (sender or admin only)"""
    
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check if user is sender
    if message.user_id != current_user.id:
        is_admin = False
        if message.group_type == "teacher":
            group = db.query(TeacherGroup).filter(TeacherGroup.id == message.teacher_group_id).first()
            if group and group.created_by == current_user.id:
                is_admin = True
        else:
            group = db.query(CelebrationGroup).filter(CelebrationGroup.id == message.celebration_group_id).first()
            if group and group.created_by == current_user.id:
                is_admin = True
        
        if not is_admin:
            raise HTTPException(status_code=403, detail="Can only delete your own messages")
    
    db.delete(message)
    db.commit()
    
    return {"success": True, "message": "Message deleted"}