# routers/search.py - COMPLETE UPDATED FILE
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from collections import defaultdict

from app.database import get_db
from app.models import TeacherGroup, CelebrationGroup, GroupMember, User
from app.schemas import GroupSearchResponse
from app.auth import get_current_active_user

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("/groups", response_model=List[GroupSearchResponse])
def search_groups(
    q: Optional[str] = Query(None, description="Search by teacher name, event title, or college"),
    district: Optional[str] = Query(None, description="Filter by district"),
    group_type: Optional[str] = Query(None, description="Filter by type: teacher or celebration"),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search for active AND PUBLIC groups across both teacher and celebration types.
    Only returns groups where is_public = True.
    """
    
    results = []
    
    # Search Teacher Groups - ONLY PUBLIC groups
    teacher_query = db.query(TeacherGroup).filter(
        TeacherGroup.status == "active",
        TeacherGroup.is_public == True  # ← NEW: Only public groups
    )
    
    if q:
        teacher_query = teacher_query.filter(
            (TeacherGroup.teacher_name.ilike(f"%{q}%")) |
            (TeacherGroup.college.ilike(f"%{q}%"))
        )
    
    if district:
        teacher_query = teacher_query.filter(TeacherGroup.district == district)
    
    teacher_groups = teacher_query.all()
    
    for group in teacher_groups:
        # Get member count
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group.id
        ).count()
        
        results.append(GroupSearchResponse(
            id=group.id,
            group_id=group.group_id,
            type="teacher",
            name=group.teacher_name,
            location=group.college or "Location TBD",
            district=group.district or "",
            event_date=group.event_date,
            member_count=member_count,
            status=group.status
        ))
    
    # Search Celebration Groups - ONLY PUBLIC groups
    celebration_query = db.query(CelebrationGroup).filter(
        CelebrationGroup.status == "active",
        CelebrationGroup.is_public == True  # ← NEW: Only public groups
    )
    
    if q:
        celebration_query = celebration_query.filter(
            (CelebrationGroup.title.ilike(f"%{q}%")) |
            (CelebrationGroup.location.ilike(f"%{q}%"))
        )
    
    if district:
        celebration_query = celebration_query.filter(CelebrationGroup.district == district)
    
    # Only include celebration groups if filter allows
    if group_type == "celebration" or group_type is None:
        celebration_groups = celebration_query.all()
        
        for group in celebration_groups:
            member_count = db.query(GroupMember).filter(
                GroupMember.celebration_group_id == group.id
            ).count()
            
            results.append(GroupSearchResponse(
                id=group.id,
                group_id=group.group_id,
                type="celebration",
                name=group.title,
                location=group.location or "Location TBD",
                district=group.district or "",
                event_date=group.event_date,
                member_count=member_count,
                status=group.status
            ))
    
    # Filter by group_type if specified
    if group_type == "teacher":
        results = [r for r in results if r.type == "teacher"]
    elif group_type == "celebration":
        results = [r for r in results if r.type == "celebration"]
    
    return results
@router.get("/districts")
def get_districts(db: Session = Depends(get_db)):
    """Get list of all districts with active groups count"""
    
    district_counts = defaultdict(int)
    
    # Count teacher groups by district (only active and public groups)
    teacher_groups = db.query(TeacherGroup).filter(
        TeacherGroup.status == "active",
        TeacherGroup.is_public == True  # ← NEW: Only public groups
    ).all()
    for group in teacher_groups:
        if group.district:
            district_counts[group.district] += 1
    
    # Count celebration groups by district (only active and public groups)
    celebration_groups = db.query(CelebrationGroup).filter(
        CelebrationGroup.status == "active",
        CelebrationGroup.is_public == True  # ← NEW: Only public groups
    ).all()
    for group in celebration_groups:
        if group.district:
            district_counts[group.district] += 1
    
    # Convert to list format
    result = [{"district": d, "count": c} for d, c in sorted(district_counts.items(), key=lambda x: x[1], reverse=True)]
    
    return result
@router.get("/group/{group_id}")
def get_group_detail(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific group"""
    
    # Check teacher groups first
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == teacher_group.id
        ).count()
        
        # Get members
        members = db.query(GroupMember, User).join(
            User, GroupMember.user_id == User.id
        ).filter(
            GroupMember.teacher_group_id == teacher_group.id
        ).all()
        
        member_list = []
        for member, user in members:
            member_list.append({
                "name": user.full_name,
                "role": member.role
            })
        
        return {
            "success": True,
            "type": "teacher",
            "group_id": teacher_group.group_id,
            "name": teacher_group.teacher_name,
            "college": teacher_group.college,
            "district": teacher_group.district,
            "event_date": teacher_group.event_date,
            "venue": teacher_group.venue,
            "memory": teacher_group.memory,
            "photos": teacher_group.photos,
            "status": teacher_group.status,
            "member_count": member_count,
            "members": member_list,
            "contribution_points": teacher_group.contribution_points,
            "lucky_friend": teacher_group.lucky_friend,
            "is_public": teacher_group.is_public  # ← NEW
        }
    
    # Check celebration groups
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        member_count = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == celebration_group.id
        ).count()
        
        members = db.query(GroupMember, User).join(
            User, GroupMember.user_id == User.id
        ).filter(
            GroupMember.celebration_group_id == celebration_group.id
        ).all()
        
        member_list = []
        for member, user in members:
            member_list.append({
                "name": user.full_name,
                "role": member.role
            })
        
        return {
            "success": True,
            "type": "celebration",
            "group_id": celebration_group.group_id,
            "name": celebration_group.title,
            "location": celebration_group.location,
            "district": celebration_group.district,
            "event_date": celebration_group.event_date,
            "venue": celebration_group.venue,
            "memory": celebration_group.memory,
            "photos": celebration_group.photos,
            "status": celebration_group.status,
            "member_count": member_count,
            "members": member_list,
            "contribution_points": celebration_group.contribution_points,
            "lucky_friend": celebration_group.lucky_friend,
            "is_public": celebration_group.is_public  # ← NEW
        }
    
    raise HTTPException(status_code=404, detail="Group not found")