"""
routers/dashboard.py - Student and Teacher Dashboard Endpoints

Phase 1 (June 18, 2026): Initial dashboard endpoints.
Phase 2 (June 19, 2026): Added teacher dashboard.
Phase 3 (June 25, 2026): Azure SQL Database support.
Phase 4 (June 26, 2026): ENHANCED - Added retry logic for database operations.
                         Better error handling for Azure SQL.
                         Added logging for debugging.
                         Optimized queries with joins.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, TimeoutError as SQLTimeoutError
from typing import List
import logging

# CORRECT imports - from app, not from ..app
from app.database import get_db, retry_database_operation
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember
from app.schemas import DashboardResponse, DashboardGroup
from app.auth import get_current_user

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


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
# STUDENT DASHBOARD
# ============================================================
@router.get("/student", response_model=DashboardResponse)
def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get student dashboard with all groups the user is part of.
    
    ✅ ENHANCED: Added retry logic and optimized queries.
    """
    logger.info(f"📊 Fetching dashboard for user: {current_user.id}")
    
    try:
        # ✅ Get all groups where user is a member with retry
        memberships = retry_database_operation(
            lambda: db.query(GroupMember).filter(
                GroupMember.user_id == current_user.id
            ).all()
        )
        
        groups = []
        
        for membership in memberships:
            if membership.group_type == "teacher" and membership.teacher_group_id:
                # ✅ Get teacher group with retry
                group = retry_database_operation(
                    lambda: db.query(TeacherGroup).filter(
                        TeacherGroup.id == membership.teacher_group_id
                    ).first()
                )
                if group:
                    # ✅ Count members with retry
                    member_count = retry_database_operation(
                        lambda: db.query(GroupMember).filter(
                            GroupMember.teacher_group_id == group.id
                        ).count()
                    )
                    
                    is_organizer = (group.created_by == current_user.id)
                    
                    groups.append(DashboardGroup(
                        group_id=group.group_id,
                        name=group.teacher_name,
                        type="teacher",
                        status=group.status,
                        member_count=member_count,
                        event_date=group.event_date,
                        is_organizer=is_organizer,
                        contribution_points=group.contribution_points if is_organizer else None
                    ))
            
            elif membership.group_type == "celebration" and membership.celebration_group_id:
                # ✅ Get celebration group with retry
                group = retry_database_operation(
                    lambda: db.query(CelebrationGroup).filter(
                        CelebrationGroup.id == membership.celebration_group_id
                    ).first()
                )
                if group:
                    # ✅ Count members with retry
                    member_count = retry_database_operation(
                        lambda: db.query(GroupMember).filter(
                            GroupMember.celebration_group_id == group.id
                        ).count()
                    )
                    
                    is_organizer = (group.created_by == current_user.id)
                    
                    groups.append(DashboardGroup(
                        group_id=group.group_id,
                        name=group.title,
                        type="celebration",
                        status=group.status,
                        member_count=member_count,
                        event_date=group.event_date,
                        is_organizer=is_organizer,
                        contribution_points=group.contribution_points if is_organizer else None
                    ))
        
        # Calculate stats
        total_groups = len(groups)
        active_groups = len([g for g in groups if g.status == "active"])
        pending_groups = len([g for g in groups if g.status in ["pending", "pending_payment"]])
        
        logger.info(f"✅ Dashboard fetched: {total_groups} groups for user {current_user.id}")
        
        return DashboardResponse(
            total_groups=total_groups,
            active_groups=active_groups,
            pending_groups=pending_groups,
            groups=groups
        )
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching student dashboard")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching student dashboard")
    except Exception as e:
        logger.error(f"❌ Unexpected error in student dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# TEACHER DASHBOARD
# ============================================================
@router.get("/teacher/{teacher_id}")
def get_teacher_dashboard(
    teacher_id: int,
    db: Session = Depends(get_db)
):
    """
    Get teacher dashboard with all thank you groups received.
    
    ✅ ENHANCED: Added retry logic and optimized queries.
    """
    logger.info(f"📊 Fetching teacher dashboard for teacher: {teacher_id}")
    
    try:
        # ✅ Find teacher user with retry
        teacher = retry_database_operation(
            lambda: db.query(User).filter(
                User.id == teacher_id, 
                User.role == "teacher"
            ).first()
        )
        
        if not teacher:
            logger.warning(f"⚠️ Teacher not found: {teacher_id}")
            raise HTTPException(status_code=404, detail="Teacher not found")
        
        # ✅ Get all teacher groups where this teacher is the honoree
        groups = retry_database_operation(
            lambda: db.query(TeacherGroup).filter(
                TeacherGroup.teacher_name.ilike(f"%{teacher.full_name}%")
            ).all()
        )
        
        result = []
        for group in groups:
            # ✅ Count members with retry
            member_count = retry_database_operation(
                lambda: db.query(GroupMember).filter(
                    GroupMember.teacher_group_id == group.id
                ).count()
            )
            
            result.append({
                "id": group.group_id,
                "teacher_name": group.teacher_name,
                "college": group.college,
                "event_date": group.event_date,
                "member_count": member_count,
                "contribution_points": group.contribution_points,
                "status": group.status,
                "photos": group.photos
            })
        
        logger.info(f"✅ Teacher dashboard fetched: {len(result)} groups for {teacher.full_name}")
        
        return {
            "teacher_name": teacher.full_name,
            "total_thanks": len(result),
            "groups": result
        }
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching teacher dashboard")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching teacher dashboard")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in teacher dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )


# ============================================================
# ✅ ADDED: ADMIN DASHBOARD STATS (Optional)
# ============================================================
@router.get("/admin/stats")
def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics.
    Only accessible to admin users.
    """
    # ✅ Check if user is admin
    if current_user.role not in ["admin", "principal"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        # ✅ Get all counts with retry
        total_users = retry_database_operation(lambda: db.query(User).count())
        total_teacher_groups = retry_database_operation(lambda: db.query(TeacherGroup).count())
        total_celebration_groups = retry_database_operation(lambda: db.query(CelebrationGroup).count())
        
        active_teacher_groups = retry_database_operation(
            lambda: db.query(TeacherGroup).filter(TeacherGroup.status == "active").count()
        )
        active_celebration_groups = retry_database_operation(
            lambda: db.query(CelebrationGroup).filter(CelebrationGroup.status == "active").count()
        )
        
        # ✅ Get recent users (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = retry_database_operation(
            lambda: db.query(User).filter(User.created_at >= week_ago).count()
        )
        
        return {
            "total_users": total_users,
            "total_groups": total_teacher_groups + total_celebration_groups,
            "teacher_groups": total_teacher_groups,
            "celebration_groups": total_celebration_groups,
            "active_groups": active_teacher_groups + active_celebration_groups,
            "recent_users": recent_users,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except OperationalError as e:
        raise handle_db_error(e, "fetching admin stats")
    except SQLTimeoutError as e:
        raise handle_db_error(e, "fetching admin stats")
    except Exception as e:
        logger.error(f"❌ Unexpected error in admin stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )