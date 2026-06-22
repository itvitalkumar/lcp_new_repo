import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app.models import User, TeacherGroup, CelebrationGroup, GroupMember, Payment
from app.schemas import (
    TeacherGroupCreate, TeacherGroupResponse, TeacherLuckyGameSubmit,
    CelebrationGroupCreate, CelebrationGroupResponse, CelebrationLuckyGameSubmit,
    LuckyGameRequest, LuckyGameResponse, JoinGroupRequest
)
from app.auth import get_current_user
from app.utils import (
    generate_lucky_numbers, generate_group_id, validate_friends_count,
    serialize_photos, serialize_friends
)

router = APIRouter(prefix="/api/groups", tags=["Groups"])


# ============ LUCKY NUMBER GAME ============
@router.post("/lucky-game", response_model=LuckyGameResponse)
def lucky_game(request: LuckyGameRequest):
    """Generate lucky numbers for friends"""
    
    is_valid, message = validate_friends_count(request.friends)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    result = generate_lucky_numbers(request.friends, request.group_type)
    
    return LuckyGameResponse(
        success=True,
        friends_with_points=result["friends_with_points"],
        contribution=result["contribution"],
        lucky_friend=result["lucky_friend"],
        label=result["label"],
        message=result["message"]
    )


# ============ CREATE GROUP (Auto-detect type) ============
@router.post("/create", response_model=dict)
def create_group(
    group_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new group - auto detects if teacher or celebration group"""
    
    group_id = generate_group_id()
    is_public = group_data.get("is_public", False)
    
    if group_data.get("teacher_name"):
        new_group = TeacherGroup(
            group_id=group_id,
            teacher_name=group_data.get("teacher_name"),
            college=group_data.get("college"),
            district=group_data.get("district"),
            event_date=group_data.get("event_date"),
            venue=group_data.get("venue"),
            pet_names=group_data.get("pet_names"),
            secret_code=group_data.get("secret_code"),
            memory=group_data.get("memory"),
            bring=group_data.get("bring"),
            dress_code=group_data.get("dress_code"),
            surprise=group_data.get("surprise"),
            note=group_data.get("note"),
            photos=None,
            contribution_points=group_data.get("amountToPay", 0),
            lucky_friend="",
            status="pending",
            created_by=current_user.id,
            is_public=is_public
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        return {
            "success": True,
            "group": {
                "id": new_group.group_id,
                "teacher_name": new_group.teacher_name,
                "status": new_group.status,
                "is_public": new_group.is_public
            }
        }
    
    elif group_data.get("title"):
        new_group = CelebrationGroup(
            group_id=group_id,
            title=group_data.get("title"),
            location=group_data.get("location"),
            district=group_data.get("district"),
            event_date=group_data.get("event_date"),
            venue=group_data.get("venue"),
            pet_names=group_data.get("pet_names"),
            secret_code=group_data.get("secret_code"),
            memory=group_data.get("memory"),
            bring=group_data.get("bring"),
            dress_code=group_data.get("dress_code"),
            surprise=group_data.get("surprise"),
            note=group_data.get("note"),
            photos=None,
            contribution_points=group_data.get("amountToPay", 0),
            lucky_friend="",
            status="pending",
            created_by=current_user.id,
            is_public=is_public
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        return {
            "success": True,
            "group": {
                "id": new_group.group_id,
                "title": new_group.title,
                "status": new_group.status,
                "is_public": new_group.is_public
            }
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid group data")


# ============ UPDATE GROUP PRIVACY (PATCH) ============
@router.patch("/update-privacy")
def update_group_privacy(
    privacy_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the is_public flag for a group (only creator can update)"""
    group_id = privacy_data.get("group_id")
    is_public = privacy_data.get("is_public", False)
    
    if not group_id:
        raise HTTPException(status_code=400, detail="group_id is required")
    
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        if teacher_group.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Only the group creator can update privacy settings")
        
        teacher_group.is_public = is_public
        db.commit()
        
        return {
            "success": True,
            "group_id": teacher_group.group_id,
            "type": "teacher",
            "is_public": teacher_group.is_public,
            "message": f"Group privacy updated to {'public' if is_public else 'private'}"
        }
    
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        if celebration_group.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Only the group creator can update privacy settings")
        
        celebration_group.is_public = is_public
        db.commit()
        
        return {
            "success": True,
            "group_id": celebration_group.group_id,
            "type": "celebration",
            "is_public": celebration_group.is_public,
            "message": f"Group privacy updated to {'public' if is_public else 'private'}"
        }
    
    raise HTTPException(status_code=404, detail="Group not found")


# ============ GET MY GROUPS (Dashboard) ============
@router.get("/my-groups", response_model=dict)
def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all groups the current user is part of"""
    
    groups_list = []
    
    teacher_memberships = db.query(GroupMember).filter(
        GroupMember.user_id == current_user.id,
        GroupMember.group_type == "teacher"
    ).all()
    
    for membership in teacher_memberships:
        group = db.query(TeacherGroup).filter(TeacherGroup.id == membership.teacher_group_id).first()
        if group:
            member_count = db.query(GroupMember).filter(
                GroupMember.teacher_group_id == group.id
            ).count()
            
            groups_list.append({
                "id": group.group_id,
                "teacher_name": group.teacher_name,
                "college": group.college,
                "event_date": group.event_date,
                "status": group.status,
                "member_count": member_count,
                "created_by": group.created_by,
                "created_by_name": group.creator.full_name if group.creator else "",
                "type": "teacher",
                "is_member": True,
                "is_creator": group.created_by == current_user.id,
                "is_public": group.is_public
            })
    
    celebration_memberships = db.query(GroupMember).filter(
        GroupMember.user_id == current_user.id,
        GroupMember.group_type == "celebration"
    ).all()
    
    for membership in celebration_memberships:
        group = db.query(CelebrationGroup).filter(CelebrationGroup.id == membership.celebration_group_id).first()
        if group:
            member_count = db.query(GroupMember).filter(
                GroupMember.celebration_group_id == group.id
            ).count()
            
            groups_list.append({
                "id": group.group_id,
                "teacher_name": group.title,
                "title": group.title,
                "location": group.location,
                "event_date": group.event_date,
                "status": group.status,
                "member_count": member_count,
                "created_by": group.created_by,
                "created_by_name": group.creator.full_name if group.creator else "",
                "type": "celebration",
                "is_member": True,
                "is_creator": group.created_by == current_user.id,
                "is_public": group.is_public
            })
    
    return {"groups": groups_list}


# ============ DELETE GROUP ============
@router.delete("/delete")
def delete_group(
    group_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a group (only creator can delete)"""
    
    group_id = group_data.get("group_id")
    
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        if teacher_group.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Only creator can delete this group")
        
        db.query(GroupMember).filter(GroupMember.teacher_group_id == teacher_group.id).delete()
        db.delete(teacher_group)
        db.commit()
        return {"success": True, "message": "Group deleted successfully"}
    
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        if celebration_group.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Only creator can delete this group")
        
        db.query(GroupMember).filter(GroupMember.celebration_group_id == celebration_group.id).delete()
        db.delete(celebration_group)
        db.commit()
        return {"success": True, "message": "Group deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Group not found")


# ============ LEAVE GROUP ============
@router.post("/leave")
def leave_group(
    leave_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave a group (user removes themselves)"""
    
    group_id = leave_data.get("group_id")
    
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        membership = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == teacher_group.id,
            GroupMember.user_id == current_user.id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="You are not a member of this group")
        
        db.delete(membership)
        db.commit()
        return {"success": True, "message": "You left the group"}
    
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        membership = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == celebration_group.id,
            GroupMember.user_id == current_user.id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="You are not a member of this group")
        
        db.delete(membership)
        db.commit()
        return {"success": True, "message": "You left the group"}
    
    raise HTTPException(status_code=404, detail="Group not found")


# ============ SEARCH GROUPS (Alias for frontend compatibility) ============
@router.get("/search")
def search_groups_alias(
    teacher_name: str = Query(None, description="Search by teacher name or title"),
    db: Session = Depends(get_db)
):
    """Search groups - alias for /api/search/groups"""
    
    results = []
    
    if teacher_name:
        teacher_groups = db.query(TeacherGroup).filter(
            TeacherGroup.teacher_name.ilike(f"%{teacher_name}%"),
            TeacherGroup.status == "active"
        ).all()
        
        for group in teacher_groups:
            member_count = db.query(GroupMember).filter(
                GroupMember.teacher_group_id == group.id
            ).count()
            
            results.append({
                "id": group.group_id,
                "teacher_name": group.teacher_name,
                "college": group.college,
                "event_date": group.event_date,
                "member_count": member_count,
                "status": group.status
            })
        
        celebration_groups = db.query(CelebrationGroup).filter(
            CelebrationGroup.title.ilike(f"%{teacher_name}%"),
            CelebrationGroup.status == "active"
        ).all()
        
        for group in celebration_groups:
            member_count = db.query(GroupMember).filter(
                GroupMember.celebration_group_id == group.id
            ).count()
            
            results.append({
                "id": group.group_id,
                "teacher_name": group.title,
                "title": group.title,
                "location": group.location,
                "event_date": group.event_date,
                "member_count": member_count,
                "status": group.status
            })
    
    return {"groups": results}


# ============ TEACHER GROUP ============
@router.post("/teacher/create", response_model=dict)
def create_teacher_group(
    group_data: TeacherGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new teacher group (Step 1)"""
    
    group_id = generate_group_id()
    photos_json = serialize_photos(group_data.photos) if group_data.photos else None
    
    new_group = TeacherGroup(
        group_id=group_id,
        teacher_name=group_data.teacher_name,
        college=group_data.college,
        district=group_data.district,
        event_date=group_data.event_date,
        venue=group_data.venue,
        pet_names=group_data.pet_names,
        secret_code=group_data.secret_code,
        memory=group_data.memory,
        bring=group_data.bring,
        dress_code=group_data.dress_code,
        surprise=group_data.surprise,
        note=group_data.note,
        photos=photos_json,
        contribution_points=0,
        lucky_friend="",
        status="pending",
        created_by=current_user.id
    )
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    return {"success": True, "group_id": group_id}


@router.post("/teacher/lucky-submit", response_model=dict)
def submit_teacher_lucky_game(
    submission: TeacherLuckyGameSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit lucky game result and activate teacher group"""
    
    group = db.query(TeacherGroup).filter(
        TeacherGroup.group_id == submission.group_id,
        TeacherGroup.created_by == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    friends_data = [{"name": f, "points": 0} for f in submission.friends]
    group.friends_list = serialize_friends(friends_data)
    group.contribution_points = submission.contribution_points
    group.lucky_friend = submission.lucky_friend
    group.status = "pending_payment"
    
    db.commit()
    
    return {
        "success": True,
        "group_id": group.group_id,
        "contribution": submission.contribution_points
    }


@router.post("/teacher/activate/{group_id}")
def activate_teacher_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate teacher group after payment"""
    
    group = db.query(TeacherGroup).filter(
        TeacherGroup.group_id == group_id,
        TeacherGroup.created_by == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.status = "active"
    db.commit()
    
    existing_member = db.query(GroupMember).filter(
        GroupMember.teacher_group_id == group.id,
        GroupMember.user_id == current_user.id
    ).first()
    
    if not existing_member:
        member = GroupMember(
            group_type="teacher",
            teacher_group_id=group.id,
            user_id=current_user.id,
            role="admin"
        )
        db.add(member)
        db.commit()
    
    return {
        "success": True,
        "invite_link": f"https://campuscentral.in/join/teacher/{group_id}",
        "message": "Group activated successfully!"
    }


# ============ CELEBRATION GROUP ============
@router.post("/celebration/create", response_model=dict)
def create_celebration_group(
    group_data: CelebrationGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new celebration group (Step 1)"""
    
    group_id = generate_group_id()
    photos_json = serialize_photos(group_data.photos) if group_data.photos else None
    
    new_group = CelebrationGroup(
        group_id=group_id,
        title=group_data.title,
        location=group_data.location,
        district=group_data.district,
        event_date=group_data.event_date,
        venue=group_data.venue,
        pet_names=group_data.pet_names,
        secret_code=group_data.secret_code,
        memory=group_data.memory,
        bring=group_data.bring,
        dress_code=group_data.dress_code,
        surprise=group_data.surprise,
        note=group_data.note,
        photos=photos_json,
        contribution_points=0,
        lucky_friend="",
        status="pending",
        created_by=current_user.id
    )
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    return {"success": True, "group_id": group_id}


@router.post("/celebration/lucky-submit", response_model=dict)
def submit_celebration_lucky_game(
    submission: CelebrationLuckyGameSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit lucky game result and activate celebration group"""
    
    group = db.query(CelebrationGroup).filter(
        CelebrationGroup.group_id == submission.group_id,
        CelebrationGroup.created_by == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    friends_data = [{"name": f, "points": 0} for f in submission.friends]
    group.friends_list = serialize_friends(friends_data)
    group.contribution_points = submission.contribution_points
    group.lucky_friend = submission.lucky_friend
    group.status = "pending_payment"
    
    db.commit()
    
    return {
        "success": True,
        "group_id": group.group_id,
        "contribution": submission.contribution_points
    }


@router.post("/celebration/activate/{group_id}")
def activate_celebration_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate celebration group after payment"""
    
    group = db.query(CelebrationGroup).filter(
        CelebrationGroup.group_id == group_id,
        CelebrationGroup.created_by == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.status = "active"
    db.commit()
    
    existing_member = db.query(GroupMember).filter(
        GroupMember.celebration_group_id == group.id,
        GroupMember.user_id == current_user.id
    ).first()
    
    if not existing_member:
        member = GroupMember(
            group_type="celebration",
            celebration_group_id=group.id,
            user_id=current_user.id,
            role="admin"
        )
        db.add(member)
        db.commit()
    
    return {
        "success": True,
        "invite_link": f"https://campuscentral.in/join/celebration/{group_id}",
        "message": "Group activated successfully!"
    }


# ============ ENHANCED: JOIN GROUP (Returns full group details) ============
@router.post("/join")
def join_group(
    request: JoinGroupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a group using invite link - Returns full group details for dashboard"""
    
    print(f"🔍 JOIN DEBUG - Group ID: {request.group_id}, Type: {request.group_type}, User ID: {current_user.id}")
    
    if request.group_type == "teacher":
        group = db.query(TeacherGroup).filter(TeacherGroup.group_id == request.group_id).first()
        
        if not group:
            print(f"❌ Teacher group not found: {request.group_id}")
            raise HTTPException(status_code=404, detail=f"Teacher group not found: {request.group_id}")
        
        print(f"✅ Found teacher group: ID={group.id}, Name={group.teacher_name}, Status={group.status}")
        
        if group.status != "active":
            print(f"❌ Group not active. Status: {group.status}")
            raise HTTPException(status_code=400, detail=f"Group is not active yet. Status: {group.status}")
        
        photos = []
        if group.photos:
            try:
                photos = json.loads(group.photos)
            except:
                photos = []
        
        # Check if already a member
        existing = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group.id,
            GroupMember.user_id == current_user.id,
            GroupMember.group_type == "teacher"
        ).first()
        
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group.id,
            GroupMember.group_type == "teacher"
        ).count()
        
        if existing:
            return {
                "success": True,
                "message": "Already a member",
                "already_member": True,
                "group_id": group.group_id,
                "group_name": group.teacher_name,
                "member_count": member_count,
                "type": "teacher",
                "college": group.college,
                "district": group.district,
                "event_date": group.event_date,
                "venue": group.venue,
                "pet_names": group.pet_names,
                "secret_code": group.secret_code,
                "memory": group.memory,
                "bring": group.bring,
                "dress_code": group.dress_code,
                "surprise": group.surprise,
                "note": group.note,
                "photos": photos,
                "contribution_points": group.contribution_points,
                "lucky_friend": group.lucky_friend,
                "status": group.status,
                "is_public": group.is_public
            }
        
        # ========== CONCURRENCY FIX ==========
        try:
            member = GroupMember(
                group_type="teacher",
                teacher_group_id=group.id,
                user_id=current_user.id,
                role="member"
            )
            db.add(member)
            db.commit()
        except IntegrityError:
            db.rollback()
            return {
                "success": True,
                "message": "Already a member",
                "already_member": True,
                "group_id": group.group_id,
                "group_name": group.teacher_name,
                "member_count": member_count,
                "type": "teacher",
                "college": group.college,
                "district": group.district,
                "event_date": group.event_date,
                "venue": group.venue,
                "pet_names": group.pet_names,
                "secret_code": group.secret_code,
                "memory": group.memory,
                "bring": group.bring,
                "dress_code": group.dress_code,
                "surprise": group.surprise,
                "note": group.note,
                "photos": photos,
                "contribution_points": group.contribution_points,
                "lucky_friend": group.lucky_friend,
                "status": group.status,
                "is_public": group.is_public
            }
        
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == group.id,
            GroupMember.group_type == "teacher"
        ).count()
        
        return {
            "success": True,
            "message": "Successfully joined the group",
            "already_member": False,
            "group_id": group.group_id,
            "group_name": group.teacher_name,
            "member_count": member_count,
            "type": "teacher",
            "college": group.college,
            "district": group.district,
            "event_date": group.event_date,
            "venue": group.venue,
            "pet_names": group.pet_names,
            "secret_code": group.secret_code,
            "memory": group.memory,
            "bring": group.bring,
            "dress_code": group.dress_code,
            "surprise": group.surprise,
            "note": group.note,
            "photos": photos,
            "contribution_points": group.contribution_points,
            "lucky_friend": group.lucky_friend,
            "status": group.status,
            "is_public": group.is_public
        }
    
    elif request.group_type == "celebration":
        group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == request.group_id).first()
        
        if not group:
            print(f"❌ Celebration group not found: {request.group_id}")
            raise HTTPException(status_code=404, detail=f"Celebration group not found: {request.group_id}")
        
        print(f"✅ Found celebration group: ID={group.id}, Title={group.title}, Status={group.status}")
        
        if group.status != "active":
            print(f"❌ Group not active. Status: {group.status}")
            raise HTTPException(status_code=400, detail=f"Group is not active yet. Status: {group.status}")
        
        photos = []
        if group.photos:
            try:
                photos = json.loads(group.photos)
            except:
                photos = []
        
        existing = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == group.id,
            GroupMember.user_id == current_user.id,
            GroupMember.group_type == "celebration"
        ).first()
        
        member_count = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == group.id,
            GroupMember.group_type == "celebration"
        ).count()
        
        if existing:
            return {
                "success": True,
                "message": "Already a member",
                "already_member": True,
                "group_id": group.group_id,
                "group_name": group.title,
                "member_count": member_count,
                "type": "celebration",
                "location": group.location,
                "district": group.district,
                "event_date": group.event_date,
                "venue": group.venue,
                "pet_names": group.pet_names,
                "secret_code": group.secret_code,
                "memory": group.memory,
                "bring": group.bring,
                "dress_code": group.dress_code,
                "surprise": group.surprise,
                "note": group.note,
                "photos": photos,
                "contribution_points": group.contribution_points,
                "lucky_friend": group.lucky_friend,
                "status": group.status,
                "is_public": group.is_public
            }
        
        # ========== CONCURRENCY FIX ==========
        try:
            member = GroupMember(
                group_type="celebration",
                celebration_group_id=group.id,
                user_id=current_user.id,
                role="member"
            )
            db.add(member)
            db.commit()
        except IntegrityError:
            db.rollback()
            return {
                "success": True,
                "message": "Already a member",
                "already_member": True,
                "group_id": group.group_id,
                "group_name": group.title,
                "member_count": member_count,
                "type": "celebration",
                "location": group.location,
                "district": group.district,
                "event_date": group.event_date,
                "venue": group.venue,
                "pet_names": group.pet_names,
                "secret_code": group.secret_code,
                "memory": group.memory,
                "bring": group.bring,
                "dress_code": group.dress_code,
                "surprise": group.surprise,
                "note": group.note,
                "photos": photos,
                "contribution_points": group.contribution_points,
                "lucky_friend": group.lucky_friend,
                "status": group.status,
                "is_public": group.is_public
            }
        
        member_count = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == group.id,
            GroupMember.group_type == "celebration"
        ).count()
        
        return {
            "success": True,
            "message": "Successfully joined the celebration",
            "already_member": False,
            "group_id": group.group_id,
            "group_name": group.title,
            "member_count": member_count,
            "type": "celebration",
            "location": group.location,
            "district": group.district,
            "event_date": group.event_date,
            "venue": group.venue,
            "pet_names": group.pet_names,
            "secret_code": group.secret_code,
            "memory": group.memory,
            "bring": group.bring,
            "dress_code": group.dress_code,
            "surprise": group.surprise,
            "note": group.note,
            "photos": photos,
            "contribution_points": group.contribution_points,
            "lucky_friend": group.lucky_friend,
            "status": group.status,
            "is_public": group.is_public
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid group_type. Must be 'teacher' or 'celebration'")


# ============ NEW: PUBLIC GROUP INFO (For join.html - NO AUTH REQUIRED) ============
@router.get("/public/{group_id}")
def get_public_group_info(
    group_id: str,
    db: Session = Depends(get_db)
):
    """
    PUBLIC endpoint - No authentication required.
    Returns group details for the invite/join page.
    """
    
    teacher_group = db.query(TeacherGroup).filter(TeacherGroup.group_id == group_id).first()
    if teacher_group:
        member_count = db.query(GroupMember).filter(
            GroupMember.teacher_group_id == teacher_group.id
        ).count()
        
        photos = []
        if teacher_group.photos:
            try:
                photos = json.loads(teacher_group.photos)
            except:
                photos = []
        
        return {
            "success": True,
            "type": "teacher",
            "group_id": teacher_group.group_id,
            "name": teacher_group.teacher_name,
            "college": teacher_group.college,
            "district": teacher_group.district,
            "event_date": teacher_group.event_date,
            "venue": teacher_group.venue,
            "pet_names": teacher_group.pet_names,
            "secret_code": teacher_group.secret_code,
            "memory": teacher_group.memory,
            "bring": teacher_group.bring,
            "dress_code": teacher_group.dress_code,
            "surprise": teacher_group.surprise,
            "note": teacher_group.note,
            "photos": photos,
            "member_count": member_count,
            "status": teacher_group.status,
            "is_active": teacher_group.status == "active",
            "contribution_points": teacher_group.contribution_points,
            "lucky_friend": teacher_group.lucky_friend,
            "is_public": teacher_group.is_public
        }
    
    celebration_group = db.query(CelebrationGroup).filter(CelebrationGroup.group_id == group_id).first()
    if celebration_group:
        member_count = db.query(GroupMember).filter(
            GroupMember.celebration_group_id == celebration_group.id
        ).count()
        
        photos = []
        if celebration_group.photos:
            try:
                photos = json.loads(celebration_group.photos)
            except:
                photos = []
        
        return {
            "success": True,
            "type": "celebration",
            "group_id": celebration_group.group_id,
            "name": celebration_group.title,
            "location": celebration_group.location,
            "district": celebration_group.district,
            "event_date": celebration_group.event_date,
            "venue": celebration_group.venue,
            "pet_names": celebration_group.pet_names,
            "secret_code": celebration_group.secret_code,
            "memory": celebration_group.memory,
            "bring": celebration_group.bring,
            "dress_code": celebration_group.dress_code,
            "surprise": celebration_group.surprise,
            "note": celebration_group.note,
            "photos": photos,
            "member_count": member_count,
            "status": celebration_group.status,
            "is_active": celebration_group.status == "active",
            "contribution_points": celebration_group.contribution_points,
            "lucky_friend": celebration_group.lucky_friend,
            "is_public": celebration_group.is_public
        }
    
    raise HTTPException(
        status_code=404, 
        detail=f"Group not found: {group_id}"
    )


# ============================================================
# PAYMENT VERIFICATION ENDPOINT (EXISTING – KEPT UNCHANGED)
# Called after successful Razorpay payment (legacy)
# ============================================================
@router.post("/payment/verify/{group_type}/{group_id}")
def verify_payment_and_activate(
    group_type: str,
    group_id: str,
    payment_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay payment and activate the group.
    Called from frontend after successful payment.
    
    Args:
        group_type: "teacher" or "celebration"
        group_id: The group ID to activate
        payment_data: Contains razorpay_payment_id, razorpay_order_id, razorpay_signature
    """
    
    # Import razorpay here to avoid circular imports
    import razorpay
    from app.config import settings
    
    # Find the group
    if group_type == "teacher":
        group = db.query(TeacherGroup).filter(
            TeacherGroup.group_id == group_id,
            TeacherGroup.created_by == current_user.id
        ).first()
    else:
        group = db.query(CelebrationGroup).filter(
            CelebrationGroup.group_id == group_id,
            CelebrationGroup.created_by == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    try:
        # Verify payment signature
        client.utility.verify_payment_signature(payment_data)
        
        # Payment verified - activate group
        group.status = "active"
        
        # Record payment in database
        payment_record = Payment(
            group_type=group_type,
            teacher_group_id=group.id if group_type == "teacher" else None,
            celebration_group_id=group.id if group_type == "celebration" else None,
            user_id=current_user.id,
            amount=group.contribution_points,
            status="success",
            razorpay_payment_id=payment_data.get("razorpay_payment_id"),
            razorpay_order_id=payment_data.get("razorpay_order_id"),
            paid_at=datetime.utcnow()
        )
        db.add(payment_record)
        
        # Add creator as member if not already
        if group_type == "teacher":
            existing_member = db.query(GroupMember).filter(
                GroupMember.teacher_group_id == group.id,
                GroupMember.user_id == current_user.id
            ).first()
        else:
            existing_member = db.query(GroupMember).filter(
                GroupMember.celebration_group_id == group.id,
                GroupMember.user_id == current_user.id
            ).first()
        
        if not existing_member:
            member = GroupMember(
                group_type=group_type,
                teacher_group_id=group.id if group_type == "teacher" else None,
                celebration_group_id=group.id if group_type == "celebration" else None,
                user_id=current_user.id,
                role="admin"
            )
            db.add(member)
        
        db.commit()
        
        return {
            "success": True,
            "message": "Payment verified and group activated successfully!",
            "group_id": group.group_id,
            "invite_link": f"https://campuscentral.in/join/{group_type}/{group_id}"
        }
        
    except Exception as e:
        print(f"Payment verification error: {e}")
        raise HTTPException(status_code=400, detail="Payment verification failed. Please contact support.")


# ============================================================
# NEW: RAZORPAY CREATE ORDER ENDPOINT
# ============================================================
@router.post("/payment/create-order")
def create_razorpay_order(
    order_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Razorpay order for group activation.
    Expected body: { "amount": int, "group_id": str, "group_type": "teacher"|"celebration" }
    """
    import razorpay
    from app.config import settings

    amount = order_data.get("amount")
    group_id = order_data.get("group_id")
    group_type = order_data.get("group_type")

    if not amount or not group_id or not group_type:
        raise HTTPException(status_code=400, detail="Missing required fields: amount, group_id, group_type")

    # Verify the group exists and belongs to the current user
    if group_type == "teacher":
        group = db.query(TeacherGroup).filter(
            TeacherGroup.group_id == group_id,
            TeacherGroup.created_by == current_user.id
        ).first()
    else:
        group = db.query(CelebrationGroup).filter(
            CelebrationGroup.group_id == group_id,
            CelebrationGroup.created_by == current_user.id
        ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Create Razorpay order
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    razorpay_order = client.order.create({
        "amount": amount * 100,  # amount in paise
        "currency": "INR",
        "receipt": f"{group_type}_{group_id}",
        "notes": {
            "group_id": group_id,
            "group_type": group_type,
            "user_id": current_user.id
        }
    })

    return {
        "success": True,
        "order_id": razorpay_order["id"],
        "amount": amount,
        "key": settings.RAZORPAY_KEY_ID
    }


# ============================================================
# NEW: RAZORPAY PAYMENT VERIFICATION ENDPOINT
# Called by frontend after Razorpay checkout success
# ============================================================
@router.post("/payment/verify-payment")
def verify_razorpay_payment(
    payment_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay payment signature and activate the group.
    Expected body: {
        "razorpay_payment_id": str,
        "razorpay_order_id": str,
        "razorpay_signature": str,
        "group_id": str,
        "group_type": "teacher"|"celebration"
    }
    """
    import razorpay
    from app.config import settings

    razorpay_payment_id = payment_data.get("razorpay_payment_id")
    razorpay_order_id = payment_data.get("razorpay_order_id")
    razorpay_signature = payment_data.get("razorpay_signature")
    group_id = payment_data.get("group_id")
    group_type = payment_data.get("group_type")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, group_id, group_type]):
        raise HTTPException(status_code=400, detail="Missing required payment data")

    # Verify group ownership
    if group_type == "teacher":
        group = db.query(TeacherGroup).filter(
            TeacherGroup.group_id == group_id,
            TeacherGroup.created_by == current_user.id
        ).first()
    else:
        group = db.query(CelebrationGroup).filter(
            CelebrationGroup.group_id == group_id,
            CelebrationGroup.created_by == current_user.id
        ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Verify signature
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    params_dict = {
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_signature": razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        print(f"Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Activate group if not already active
    if group.status != "active":
        group.status = "active"
        # Add creator as member (if not already)
        if group_type == "teacher":
            existing = db.query(GroupMember).filter(
                GroupMember.teacher_group_id == group.id,
                GroupMember.user_id == current_user.id
            ).first()
        else:
            existing = db.query(GroupMember).filter(
                GroupMember.celebration_group_id == group.id,
                GroupMember.user_id == current_user.id
            ).first()
        if not existing:
            new_member = GroupMember(
                group_type=group_type,
                teacher_group_id=group.id if group_type == "teacher" else None,
                celebration_group_id=group.id if group_type == "celebration" else None,
                user_id=current_user.id,
                role="admin"
            )
            db.add(new_member)

        # Record payment
        payment_record = Payment(
            group_type=group_type,
            teacher_group_id=group.id if group_type == "teacher" else None,
            celebration_group_id=group.id if group_type == "celebration" else None,
            user_id=current_user.id,
            amount=group.contribution_points,
            status="success",
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            paid_at=datetime.utcnow()
        )
        db.add(payment_record)
        db.commit()

    return {
        "success": True,
        "group_id": group.group_id,
        "message": "Payment verified and group activated successfully"
    }