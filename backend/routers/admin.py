from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

# CORRECT imports - from app, not from ..app
from app.database import get_db
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember, SuccessStory, Payment
from app.auth import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/dashboard")
def get_admin_dashboard(
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    
    # Count all entities
    total_users = db.query(User).count()
    total_teacher_groups = db.query(TeacherGroup).count()
    total_celebration_groups = db.query(CelebrationGroup).count()
    total_active_groups = db.query(TeacherGroup).filter(TeacherGroup.status == "active").count() + \
                          db.query(CelebrationGroup).filter(CelebrationGroup.status == "active").count()
    total_stories = db.query(SuccessStory).count()
    pending_stories = db.query(SuccessStory).filter(SuccessStory.is_approved == False).count()
    
    # Recent users (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = db.query(User).filter(User.created_at >= week_ago).count()
    
    return {
        "total_users": total_users,
        "total_teacher_groups": total_teacher_groups,
        "total_celebration_groups": total_celebration_groups,
        "total_active_groups": total_active_groups,
        "total_stories": total_stories,
        "pending_stories": pending_stories,
        "recent_users": recent_users
    }


@router.get("/users")
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users with pagination (admin only)"""
    
    users = db.query(User).offset(skip).limit(limit).all()
    
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


@router.get("/groups/teacher")
def get_all_teacher_groups(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all teacher groups (admin only)"""
    
    groups = db.query(TeacherGroup).offset(skip).limit(limit).all()
    
    result = []
    for g in groups:
        member_count = db.query(GroupMember).filter(GroupMember.teacher_group_id == g.id).count()
        result.append({
            "id": g.id,
            "group_id": g.group_id,
            "teacher_name": g.teacher_name,
            "college": g.college,
            "district": g.district,
            "status": g.status,
            "contribution_points": g.contribution_points,
            "member_count": member_count,
            "created_at": g.created_at
        })
    
    return result


@router.get("/groups/celebration")
def get_all_celebration_groups(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all celebration groups (admin only)"""
    
    groups = db.query(CelebrationGroup).offset(skip).limit(limit).all()
    
    result = []
    for g in groups:
        member_count = db.query(GroupMember).filter(GroupMember.celebration_group_id == g.id).count()
        result.append({
            "id": g.id,
            "group_id": g.group_id,
            "title": g.title,
            "location": g.location,
            "district": g.district,
            "status": g.status,
            "contribution_points": g.contribution_points,
            "member_count": member_count,
            "created_at": g.created_at
        })
    
    return result


@router.delete("/user/{user_id}")
def delete_user(
    user_id: int,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a user and all their associated data (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't allow deleting yourself
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    db.delete(user)
    db.commit()
    
    return {"success": True, "message": f"User {user.email} deleted successfully"}


@router.delete("/group/{group_type}/{group_id}")
def delete_group(
    group_type: str,
    group_id: str,
    current_user = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a group by its ID (admin only)"""
    
    if group_type == "teacher":
        group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Teacher group not found")
        db.delete(group)
    elif group_type == "celebration":
        group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Celebration group not found")
        db.delete(group)
    else:
        raise HTTPException(status_code=400, detail="Invalid group type")
    
    db.commit()
    
    return {"success": True, "message": f"Group {group_id} deleted successfully"}


@router.get("/export/users")
def export_users_csv(current_user = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Export all users as CSV (admin only)"""
    
    import csv
    from fastapi.responses import StreamingResponse
    from io import StringIO
    
    users = db.query(User).all()
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Email", "Full Name", "Role", "College", "District", "Created At"])
    
    for u in users:
        writer.writerow([u.id, u.email, u.full_name, u.role, u.college or "", u.district or "", u.created_at])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"}
    )# Placeholder - Code will be added
