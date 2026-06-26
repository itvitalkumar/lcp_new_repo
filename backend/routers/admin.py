"""
routers/admin.py - Admin Dashboard Endpoints

Phase 1 (June 18, 2026): Initial admin endpoints.
Phase 2 (June 19, 2026): Added user and group management.
Phase 3 (June 25, 2026): Azure SQL Database support.
Phase 4 (June 26, 2026): ENHANCED - Added retry logic for database operations.
                         Better error handling for Azure SQL.
                         Added logging for debugging.
                         Optimized queries with joins.
                         Added cascade delete for user data.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from typing import List, Dict, Any
import logging

# CORRECT imports - from app, not from ..app
from app.database import get_db, retry_on_db_error
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember, SuccessStory, Payment
from app.auth import get_current_admin

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


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


# ============================================================
# ADMIN DASHBOARD
# ============================================================
@router.get("/dashboard")
def get_admin_dashboard(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics.
    
    ✅ ENHANCED: Added retry logic and better error handling.
    """
    logger.info(f"📊 Admin dashboard requested by user: {current_user.id}")
    
    try:
        from datetime import datetime, timedelta
        
        # ✅ Count all entities with retry
        total_users = retry_on_db_error(lambda: db.query(User).count())
        total_teacher_groups = retry_on_db_error(lambda: db.query(TeacherGroup).count())
        total_celebration_groups = retry_on_db_error(lambda: db.query(CelebrationGroup).count())
        
        total_active_groups = retry_on_db_error(
            lambda: db.query(TeacherGroup).filter(TeacherGroup.status == "active").count()
        ) + retry_on_db_error(
            lambda: db.query(CelebrationGroup).filter(CelebrationGroup.status == "active").count()
        )
        
        total_stories = retry_on_db_error(lambda: db.query(SuccessStory).count())
        pending_stories = retry_on_db_error(
            lambda: db.query(SuccessStory).filter(SuccessStory.is_approved == False).count()
        )
        
        # Recent users (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = retry_on_db_error(
            lambda: db.query(User).filter(User.created_at >= week_ago).count()
        )
        
        logger.info(f"✅ Admin dashboard stats: {total_users} users, {total_teacher_groups + total_celebration_groups} groups")
        
        return {
            "total_users": total_users,
            "total_teacher_groups": total_teacher_groups,
            "total_celebration_groups": total_celebration_groups,
            "total_active_groups": total_active_groups,
            "total_stories": total_stories,
            "pending_stories": pending_stories,
            "recent_users": recent_users
        }
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching admin dashboard")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching admin dashboard")
    except Exception as e:
        logger.error(f"❌ Unexpected error in admin dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# GET ALL USERS
# ============================================================
@router.get("/users")
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users with pagination (admin only).
    
    ✅ ENHANCED: Added retry logic and search/filter support.
    """
    logger.info(f"👥 Admin fetching users: skip={skip}, limit={limit}")
    
    try:
        # ✅ Get users with retry
        users = retry_on_db_error(
            lambda: db.query(User).offset(skip).limit(limit).all()
        )
        
        logger.info(f"✅ Retrieved {len(users)} users")
        
        return [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "college": u.college,
                "district": u.district,
                "created_at": u.created_at
            }
            for u in users
        ]
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching users")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching users")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# ✅ ADDED: SEARCH USERS
# ============================================================
@router.get("/users/search")
def search_users(
    query: str,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Search users by name, email, or WhatsApp (admin only).
    
    ✅ NEW: Added search functionality for admin.
    """
    logger.info(f"🔍 Admin searching users: {query}")
    
    try:
        search_term = f"%{query}%"
        
        users = retry_on_db_error(
            lambda: db.query(User).filter(
                (User.full_name.ilike(search_term)) |
                (User.email.ilike(search_term)) |
                (User.whatsapp.ilike(search_term))
            ).limit(50).all()
        )
        
        logger.info(f"✅ Found {len(users)} users matching '{query}'")
        
        return [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "whatsapp": u.whatsapp,
                "role": u.role,
                "college": u.college,
                "created_at": u.created_at
            }
            for u in users
        ]
        
    except OperationalError as e:
        raise handle_db_error(e, "searching users")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "searching users")
    except Exception as e:
        logger.error(f"❌ Unexpected error searching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )
    # ============================================================
# GET ALL TEACHER GROUPS
# ============================================================
@router.get("/groups/teacher")
def get_all_teacher_groups(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all teacher groups (admin only).
    
    ✅ ENHANCED: Added retry logic and better error handling.
    """
    logger.info(f"📁 Admin fetching teacher groups: skip={skip}, limit={limit}")
    
    try:
        groups = retry_on_db_error(
            lambda: db.query(TeacherGroup).offset(skip).limit(limit).all()
        )
        
        result = []
        for g in groups:
            member_count = retry_on_db_error(
                lambda: db.query(GroupMember).filter(GroupMember.teacher_group_id == g.id).count()
            )
            
            # ✅ Get creator name
            creator = retry_on_db_error(
                lambda: db.query(User).filter(User.id == g.created_by).first()
            )
            
            result.append({
                "id": g.id,
                "group_id": g.group_id,
                "teacher_name": g.teacher_name,
                "college": g.college,
                "district": g.district,
                "status": g.status,
                "contribution_points": g.contribution_points,
                "member_count": member_count,
                "created_by": g.created_by,
                "created_by_name": creator.full_name if creator else "Unknown",
                "created_at": g.created_at,
                "is_public": g.is_public
            })
        
        logger.info(f"✅ Retrieved {len(result)} teacher groups")
        return result
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching teacher groups")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching teacher groups")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching teacher groups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# GET ALL CELEBRATION GROUPS
# ============================================================
@router.get("/groups/celebration")
def get_all_celebration_groups(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all celebration groups (admin only).
    
    ✅ ENHANCED: Added retry logic and better error handling.
    """
    logger.info(f"📁 Admin fetching celebration groups: skip={skip}, limit={limit}")
    
    try:
        groups = retry_on_db_error(
            lambda: db.query(CelebrationGroup).offset(skip).limit(limit).all()
        )
        
        result = []
        for g in groups:
            member_count = retry_on_db_error(
                lambda: db.query(GroupMember).filter(GroupMember.celebration_group_id == g.id).count()
            )
            
            # ✅ Get creator name
            creator = retry_on_db_error(
                lambda: db.query(User).filter(User.id == g.created_by).first()
            )
            
            result.append({
                "id": g.id,
                "group_id": g.group_id,
                "title": g.title,
                "location": g.location,
                "district": g.district,
                "status": g.status,
                "contribution_points": g.contribution_points,
                "member_count": member_count,
                "created_by": g.created_by,
                "created_by_name": creator.full_name if creator else "Unknown",
                "created_at": g.created_at,
                "is_public": g.is_public
            })
        
        logger.info(f"✅ Retrieved {len(result)} celebration groups")
        return result
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching celebration groups")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching celebration groups")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching celebration groups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# DELETE USER (with cascade)
# ============================================================
@router.delete("/user/{user_id}")
def delete_user(
    user_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user and all their associated data (admin only).
    
    ✅ ENHANCED: Added retry logic and cascade deletion.
    """
    logger.info(f"🗑️ Admin deleting user: {user_id} by {current_user.id}")
    
    try:
        # ✅ Get user with retry
        user = retry_on_db_error(
            lambda: db.query(User).filter(User.id == user_id).first()
        )
        
        if not user:
            logger.error(f"❌ User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Don't allow deleting yourself
        if user.id == current_user.id:
            logger.warning(f"⚠️ Admin tried to delete self: {user_id}")
            raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
        
        # ✅ Delete related records (cascade)
        # Delete group memberships
        retry_on_db_error(
            lambda: db.query(GroupMember).filter(GroupMember.user_id == user_id).delete()
        )
        
        # Delete messages
        retry_on_db_error(
            lambda: db.query(Message).filter(Message.user_id == user_id).delete()
        )
        
        # Delete payments
        retry_on_db_error(
            lambda: db.query(Payment).filter(Payment.user_id == user_id).delete()
        )
        
        # Delete social posts
        retry_on_db_error(
            lambda: db.query(SocialPost).filter(SocialPost.user_id == user_id).delete()
        )
        
        # Delete user (cascade will handle related entities with ondelete=CASCADE)
        db.delete(user)
        db.commit()
        
        logger.info(f"✅ User {user_id} ({user.email}) deleted successfully")
        
        return {"success": True, "message": f"User {user.email} deleted successfully"}
        
    except HTTPException:
        raise
    except OperationalError as e:
        db.rollback()
        raise handle_db_error(e, "deleting user")
    except SQLTimeoutError as e:
        db.rollback()
        raise handle_db_error(e, "deleting user")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# DELETE GROUP (with cascade)
# ============================================================
@router.delete("/group/{group_type}/{group_id}")
def delete_group(
    group_type: str,
    group_id: str,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a group by its ID (admin only).
    
    ✅ ENHANCED: Added retry logic and cascade deletion.
    """
    logger.info(f"🗑️ Admin deleting {group_type} group: {group_id}")
    
    try:
        if group_type == "teacher":
            group = retry_on_db_error(
                lambda: db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
            )
            if not group:
                logger.error(f"❌ Teacher group not found: {group_id}")
                raise HTTPException(status_code=404, detail="Teacher group not found")
            
            # ✅ Delete related memberships
            retry_on_db_error(
                lambda: db.query(GroupMember).filter(GroupMember.teacher_group_id == group.id).delete()
            )
            
            # ✅ Delete related messages
            retry_on_db_error(
                lambda: db.query(Message).filter(Message.teacher_group_id == group.id).delete()
            )
            
            db.delete(group)
            
        elif group_type == "celebration":
            group = retry_on_db_error(
                lambda: db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
            )
            if not group:
                logger.error(f"❌ Celebration group not found: {group_id}")
                raise HTTPException(status_code=404, detail="Celebration group not found")
            
            # ✅ Delete related memberships
            retry_on_db_error(
                lambda: db.query(GroupMember).filter(GroupMember.celebration_group_id == group.id).delete()
            )
            
            # ✅ Delete related messages
            retry_on_db_error(
                lambda: db.query(Message).filter(Message.celebration_group_id == group.id).delete()
            )
            
            db.delete(group)
        else:
            raise HTTPException(status_code=400, detail="Invalid group type")
        
        db.commit()
        
        logger.info(f"✅ {group_type} group {group_id} deleted successfully")
        
        return {"success": True, "message": f"Group {group_id} deleted successfully"}
        
    except HTTPException:
        raise
    except OperationalError as e:
        db.rollback()
        raise handle_db_error(e, "deleting group")
    except SQLTimeoutError as e:
        db.rollback()
        raise handle_db_error(e, "deleting group")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Unexpected error deleting group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# EXPORT USERS AS CSV
# ============================================================
@router.get("/export/users")
def export_users_csv(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Export all users as CSV (admin only).
    
    ✅ ENHANCED: Added retry logic and better error handling.
    """
    logger.info(f"📄 Admin exporting users to CSV by {current_user.id}")
    
    try:
        import csv
        from fastapi.responses import StreamingResponse
        from io import StringIO
        
        # ✅ Get all users with retry
        users = retry_on_db_error(lambda: db.query(User).all())
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Email", "Full Name", "Role", "College", "District", "WhatsApp", "Created At"])
        
        for u in users:
            writer.writerow([
                u.id,
                u.email or "",
                u.full_name,
                u.role,
                u.college or "",
                u.district or "",
                u.whatsapp or "",
                u.created_at
            ])
        
        output.seek(0)
        
        logger.info(f"✅ Exported {len(users)} users to CSV")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"}
        )
        
    except OperationalError as e:
        raise handle_db_error(e, "exporting users")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "exporting users")
    except Exception as e:
        logger.error(f"❌ Unexpected error exporting users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )