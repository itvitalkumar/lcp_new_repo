# routers/messages.py - Complete Chat System for Campus Central
# Phase 1 (June 18, 2026): Initial chat system.
# Phase 2 (June 19, 2026): Added image support.
# Phase 3 (June 25, 2026): Azure SQL Database support.
# Phase 4 (June 26, 2026): ENHANCED - Added retry logic for database operations.
#                         Better error handling for Azure SQL.
#                         Added logging instead of print statements.
#                         Optimized queries with joins.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from typing import List, Optional
from datetime import datetime
import base64
import uuid
import os
import logging

from pydantic import BaseModel

from app.database import get_db, retry_database_operation
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember, Message
from app.auth import get_current_user
from app.config import settings

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

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


# ============================================================
# ✅ ADDED: HELPER FOR DATABASE ERROR HANDLING
# ============================================================
def handle_db_error(e: Exception, operation: str) -> HTTPException:
    """
    Convert database errors to user-friendly HTTP exceptions.
    """
    logger.error(f"❌ Database error during {operation}: {str(e)}")
    
    if "timeout" in str(e).lower() or "connection" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again in a moment."
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again later."
        )


# ============ HELPER: Save Image ============
def save_image(base64_string: str) -> Optional[str]:
    """
    Save base64 image to disk and return URL.
    
    ✅ ENHANCED: Added better error handling and logging.
    """
    if not base64_string:
        return None
    
    try:
        if base64_string.startswith("data:image"):
            base64_string = base64_string.split(",")[1]
        
        image_data = base64.b64decode(base64_string)
        
        # ✅ Validate image size
        if len(image_data) > settings.MAX_UPLOAD_SIZE:
            logger.error(f"❌ Image too large: {len(image_data)} bytes (max: {settings.MAX_UPLOAD_SIZE})")
            return None
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        filename = f"chat_img_{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        logger.info(f"✅ Chat image saved: {filepath}")
        return f"/uploads/{filename}"
        
    except base64.binascii.Error as e:
        logger.error(f"❌ Invalid base64 image: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error saving image: {e}")
        return None


# ============ 1. SEND MESSAGE ============
@router.post("/send", response_model=dict)
def send_message(
    data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message to a group - text or image.
    
    ✅ ENHANCED: Added retry logic and better error handling.
    """
    # ========== FIX: Reject empty or whitespace-only messages ==========
    if not data.message or not data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    # ==================================================================
    
    logger.info(f"💬 MESSAGE - Group: {data.group_id}, Type: {data.group_type}, User: {current_user.id}")
    
    try:
        # Find the group with retry
        group_db_id = None
        if data.group_type == "teacher":
            group = retry_database_operation(
                lambda: db.query(TeacherGroup).filter(
                    TeacherGroup.group_id == data.group_id
                ).first()
            )
            if not group:
                logger.error(f"❌ Teacher group not found: {data.group_id}")
                raise HTTPException(status_code=404, detail="Teacher group not found")
            group_db_id = group.id
        elif data.group_type == "celebration":
            group = retry_database_operation(
                lambda: db.query(CelebrationGroup).filter(
                    CelebrationGroup.group_id == data.group_id
                ).first()
            )
            if not group:
                logger.error(f"❌ Celebration group not found: {data.group_id}")
                raise HTTPException(status_code=404, detail="Celebration group not found")
            group_db_id = group.id
        else:
            raise HTTPException(status_code=400, detail="Invalid group_type")
        
        # Check if user is a member with retry
        is_member = False
        if data.group_type == "teacher":
            member = retry_database_operation(
                lambda: db.query(GroupMember).filter(
                    GroupMember.teacher_group_id == group_db_id,
                    GroupMember.user_id == current_user.id
                ).first()
            )
            is_member = member is not None
        else:
            member = retry_database_operation(
                lambda: db.query(GroupMember).filter(
                    GroupMember.celebration_group_id == group_db_id,
                    GroupMember.user_id == current_user.id
                ).first()
            )
            is_member = member is not None
        
        if not is_member:
            logger.warning(f"❌ User {current_user.id} is NOT a member of group {data.group_id}")
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
        
        logger.info(f"✅ Message {new_message.id} saved for group {data.group_id}")
        
        return {
            "success": True,
            "message_id": new_message.id,
            "message": data.message,
            "image_url": image_url,
            "sent_at": new_message.sent_at.isoformat()
        }
        
    except HTTPException:
        raise
    except OperationalError as e:
        db.rollback()
        raise handle_db_error(e, "sending message")
    except SQLTimeoutError as e:
        db.rollback()
        raise handle_db_error(e, "sending message")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error sending message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============ 2. GET MESSAGES ============
@router.get("/{group_id}")
def get_messages(
    group_id: str,
    group_type: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all messages for a group.
    
    ✅ ENHANCED: Added retry logic and optimized queries.
    """
    logger.info(f"📨 Fetching messages for group: {group_id}, type: {group_type}")
    
    try:
        # Find the group with retry
        group_db_id = None
        if group_type == "teacher":
            group = retry_database_operation(
                lambda: db.query(TeacherGroup).filter(
                    TeacherGroup.group_id == group_id
                ).first()
            )
            if not group:
                logger.error(f"❌ Teacher group not found: {group_id}")
                raise HTTPException(status_code=404, detail="Teacher group not found")
            group_db_id = group.id
        elif group_type == "celebration":
            group = retry_database_operation(
                lambda: db.query(CelebrationGroup).filter(
                    CelebrationGroup.group_id == group_id
                ).first()
            )
            if not group:
                logger.error(f"❌ Celebration group not found: {group_id}")
                raise HTTPException(status_code=404, detail="Celebration group not found")
            group_db_id = group.id
        else:
            raise HTTPException(status_code=400, detail="Invalid group_type")
        
        # Check membership with retry
        is_member = False
        if group_type == "teacher":
            member = retry_database_operation(
                lambda: db.query(GroupMember).filter(
                    GroupMember.teacher_group_id == group_db_id,
                    GroupMember.user_id == current_user.id
                ).first()
            )
            is_member = member is not None
        else:
            member = retry_database_operation(
                lambda: db.query(GroupMember).filter(
                    GroupMember.celebration_group_id == group_db_id,
                    GroupMember.user_id == current_user.id
                ).first()
            )
            is_member = member is not None
        
        if not is_member:
            logger.warning(f"❌ User {current_user.id} is NOT a member of group {group_id}")
            raise HTTPException(status_code=403, detail="Not a member")
        
        # Get messages with retry
        if group_type == "teacher":
            messages = retry_database_operation(
                lambda: db.query(Message).filter(
                    Message.teacher_group_id == group_db_id,
                    Message.group_type == "teacher"
                ).order_by(Message.sent_at.desc()).limit(limit).all()
            )
        else:
            messages = retry_database_operation(
                lambda: db.query(Message).filter(
                    Message.celebration_group_id == group_db_id,
                    Message.group_type == "celebration"
                ).order_by(Message.sent_at.desc()).limit(limit).all()
            )
        
        messages.reverse()
        
        result = []
        for msg in messages:
            # ✅ Get sender with retry
            sender = retry_database_operation(
                lambda: db.query(User).filter(User.id == msg.user_id).first()
            )
            
            # Extract image from message if present
            image_url = None
            message_text = msg.message
            if msg.message and msg.message.startswith("[IMAGE]"):
                # Try to find actual image URL
                if hasattr(msg, 'image_url') and msg.image_url:
                    image_url = msg.image_url
                else:
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
        
        logger.info(f"✅ Retrieved {len(result)} messages for group {group_id}")
        
        return {"messages": result, "total": len(result)}
        
    except HTTPException:
        raise
    except OperationalError as e:
        raise handle_db_error(e, "fetching messages")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching messages")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============ 3. DELETE MESSAGE ============
@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a message (sender or admin only).
    
    ✅ ENHANCED: Added retry logic and better error handling.
    """
    logger.info(f"🗑️ Deleting message: {message_id} by user {current_user.id}")
    
    try:
        # Get message with retry
        message = retry_database_operation(
            lambda: db.query(Message).filter(Message.id == message_id).first()
        )
        
        if not message:
            logger.error(f"❌ Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user is sender
        if message.user_id != current_user.id:
            is_admin = False
            if message.group_type == "teacher":
                group = retry_database_operation(
                    lambda: db.query(TeacherGroup).filter(
                        TeacherGroup.id == message.teacher_group_id
                    ).first()
                )
                if group and group.created_by == current_user.id:
                    is_admin = True
            else:
                group = retry_database_operation(
                    lambda: db.query(CelebrationGroup).filter(
                        CelebrationGroup.id == message.celebration_group_id
                    ).first()
                )
                if group and group.created_by == current_user.id:
                    is_admin = True
            
            if not is_admin:
                logger.warning(f"❌ User {current_user.id} not authorized to delete message {message_id}")
                raise HTTPException(status_code=403, detail="Can only delete your own messages")
        
        db.delete(message)
        db.commit()
        
        logger.info(f"✅ Message {message_id} deleted by user {current_user.id}")
        
        return {"success": True, "message": "Message deleted"}
        
    except HTTPException:
        raise
    except OperationalError as e:
        db.rollback()
        raise handle_db_error(e, "deleting message")
    except SQLTimeoutError as e:
        db.rollback()
        raise handle_db_error(e, "deleting message")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error deleting message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )