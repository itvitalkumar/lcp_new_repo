# Placeholder - Code will be added
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# CORRECT imports - from app, not from ..app
from app.database import get_db
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember
from app.schemas import DashboardResponse, DashboardGroup
from app.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/student", response_model=DashboardResponse)
def get_student_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get student dashboard with all groups the user is part of"""
    
    # Get all groups where user is a member
    memberships = db.query(GroupMember).filter(GroupMember.user_id == current_user.id).all()
    
    groups = []
    
    for membership in memberships:
        if membership.group_type == "teacher" and membership.teacher_group_id:
            group = db.query(TeacherGroup).filter(TeacherGroup.id == membership.teacher_group_id).first()
            if group:
                # Count members
                member_count = db.query(GroupMember).filter(
                    GroupMember.teacher_group_id == group.id
                ).count()
                
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
            group = db.query(CelebrationGroup).filter(CelebrationGroup.id == membership.celebration_group_id).first()
            if group:
                member_count = db.query(GroupMember).filter(
                    GroupMember.celebration_group_id == group.id
                ).count()
                
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
    
    return DashboardResponse(
        total_groups=total_groups,
        active_groups=active_groups,
        pending_groups=pending_groups,
        groups=groups
    )


@router.get("/teacher/{teacher_id}")
def get_teacher_dashboard(
    teacher_id: int,
    db: Session = Depends(get_db)
):
    """Get teacher dashboard with all thank you groups received"""
    
    # Find teacher user
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Get all teacher groups where this teacher is the honoree
    groups = db.query(TeacherGroup).filter(
        TeacherGroup.teacher_name.ilike(f"%{teacher.full_name}%")
    ).all()
    
    result = []
    for group in groups:
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group.id
        ).count()
        
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
    
    return {
        "teacher_name": teacher.full_name,
        "total_thanks": len(result),
        "groups": result
    }