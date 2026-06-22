from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from typing import Optional

from app.database import get_db
from app.models import TeacherGroup, CelebrationGroup, GroupMember
from app.schemas import PublicGroupResponse

router = APIRouter(prefix="/api/public", tags=["Public"])


@router.get("/group/{group_id}", response_model=PublicGroupResponse)
def get_public_group_info(
    group_id: str,
    db: Session = Depends(get_db)
):
    """
    PUBLIC endpoint - No authentication required.
    Returns group details for the invite/join page.
    Used by join.html to display group information before user logs in.
    
    This endpoint works for both:
    - Teacher groups (Thank Teacher feature)
    - Celebration groups (Celebrate Together feature)
    """
    
    # First check Teacher Groups
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        # Count members
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == teacher_group.id
        ).count()
        
        # Parse photos if stored as JSON
        photos = []
        if teacher_group.photos:
            try:
                photos = json.loads(teacher_group.photos)
            except (json.JSONDecodeError, TypeError):
                photos = []
        
        return PublicGroupResponse(
            success=True,
            type="teacher",
            group_id=teacher_group.group_id,
            name=teacher_group.teacher_name,
            member_count=member_count,
            status=teacher_group.status,
            is_active=teacher_group.status == "active",
            event_date=teacher_group.event_date,
            venue=teacher_group.venue,
            college=teacher_group.college,
            location=None,  # Not applicable for teacher groups
            district=teacher_group.district,
            pet_names=teacher_group.pet_names,
            secret_code=teacher_group.secret_code,
            memory=teacher_group.memory,
            bring=teacher_group.bring,
            dress_code=teacher_group.dress_code,
            surprise=teacher_group.surprise,
            note=teacher_group.note,
            photos=photos if photos else None,
            contribution_points=teacher_group.contribution_points,
            lucky_friend=teacher_group.lucky_friend
        )
    
    # Then check Celebration Groups
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        # Count members
        member_count = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == celebration_group.id
        ).count()
        
        # Parse photos if stored as JSON
        photos = []
        if celebration_group.photos:
            try:
                photos = json.loads(celebration_group.photos)
            except (json.JSONDecodeError, TypeError):
                photos = []
        
        return PublicGroupResponse(
            success=True,
            type="celebration",
            group_id=celebration_group.group_id,
            name=celebration_group.title,
            member_count=member_count,
            status=celebration_group.status,
            is_active=celebration_group.status == "active",
            event_date=celebration_group.event_date,
            venue=celebration_group.venue,
            college=None,  # Not applicable for celebration groups
            location=celebration_group.location,
            district=celebration_group.district,
            pet_names=celebration_group.pet_names,
            secret_code=celebration_group.secret_code,
            memory=celebration_group.memory,
            bring=celebration_group.bring,
            dress_code=celebration_group.dress_code,
            surprise=celebration_group.surprise,
            note=celebration_group.note,
            photos=photos if photos else None,
            contribution_points=celebration_group.contribution_points,
            lucky_friend=celebration_group.lucky_friend
        )
    
    # Group not found
    raise HTTPException(
        status_code=404,
        detail=f"Group not found: {group_id}. The invite link may be invalid or the group has been deleted."
    )