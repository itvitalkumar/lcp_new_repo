from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/marriage", tags=["Marriage Staffing Marketplace"])

# ============ MODELS ============
class JobPost(BaseModel):
    event_date: str
    event_location: str
    event_type: str  # wedding, reception, engagement, other
    role_needed: str  # serving, dancing, cleaning, decoration, all
    number_of_staff: int
    pay_per_staff: int
    description: Optional[str] = None
    contact_whatsapp: str

class JobResponse(BaseModel):
    id: int
    posted_by: str
    posted_by_college: str
    event_date: str
    event_location: str
    event_type: str
    role_needed: str
    number_of_staff: int
    pay_per_staff: int
    description: Optional[str]
    contact_whatsapp: str
    created_at: str
    applicants_count: int

class StudentApplication(BaseModel):
    job_id: int
    message: Optional[str] = None

class StudentProfile(BaseModel):
    skills: List[str]
    availability: str  # full_time, weekend_only, flexible
    experience: Optional[str] = None
    whatsapp: str


# In-memory storage
jobs_db = []
jobs_counter = 0
applications_db = []
student_profiles_db = []


@router.post("/post-job", response_model=dict)
def post_job(
    data: JobPost,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post a job for marriage event staffing (₹99 + commission)"""
    global jobs_counter
    jobs_counter += 1
    
    jobs_db.append({
        "id": jobs_counter,
        "posted_by_id": current_user.id,
        "posted_by": current_user.full_name,
        "posted_by_college": getattr(current_user, "college", "Not specified"),
        "event_date": data.event_date,
        "event_location": data.event_location,
        "event_type": data.event_type,
        "role_needed": data.role_needed,
        "number_of_staff": data.number_of_staff,
        "pay_per_staff": data.pay_per_staff,
        "description": data.description,
        "contact_whatsapp": data.contact_whatsapp,
        "created_at": datetime.now().isoformat(),
        "applicants_count": 0,
        "is_active": True,
        "payment_status": "pending"
    })
    
    return {"success": True, "id": jobs_counter, "message": "Job posted successfully. Payment required to activate."}


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    location: Optional[str] = Query(None, description="Filter by location"),
    db: Session = Depends(get_db)
):
    """Get all active job postings"""
    
    results = [j for j in jobs_db if j.get("is_active", True) and j.get("payment_status") == "paid"]
    
    if event_type:
        results = [j for j in results if j["event_type"] == event_type]
    
    if location:
        results = [j for j in results if location.lower() in j["event_location"].lower()]
    
    results.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [
        JobResponse(
            id=j["id"],
            posted_by=j["posted_by"],
            posted_by_college=j["posted_by_college"],
            event_date=j["event_date"],
            event_location=j["event_location"],
            event_type=j["event_type"],
            role_needed=j["role_needed"],
            number_of_staff=j["number_of_staff"],
            pay_per_staff=j["pay_per_staff"],
            description=j.get("description"),
            contact_whatsapp=j["contact_whatsapp"],
            created_at=j["created_at"],
            applicants_count=j.get("applicants_count", 0)
        )
        for j in results
    ]


@router.post("/student/profile")
def create_student_profile(
    data: StudentProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create student profile for job seeking"""
    
    existing = next((s for s in student_profiles_db if s["user_id"] == current_user.id), None)
    
    profile_data = {
        "user_id": current_user.id,
        "name": current_user.full_name,
        "college": getattr(current_user, "college", "Not specified"),
        "skills": data.skills,
        "availability": data.availability,
        "experience": data.experience,
        "whatsapp": data.whatsapp,
        "updated_at": datetime.now().isoformat()
    }
    
    if existing:
        existing.update(profile_data)
        return {"success": True, "message": "Profile updated"}
    
    student_profiles_db.append(profile_data)
    return {"success": True, "message": "Profile created"}


@router.post("/apply")
def apply_for_job(
    application: StudentApplication,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply for a job"""
    
    job = next((j for j in jobs_db if j["id"] == application.job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("payment_status") != "paid":
        raise HTTPException(status_code=400, detail="Job not activated yet")
    
    # Check if already applied
    existing = next((a for a in applications_db 
                     if a["job_id"] == application.job_id and a["student_id"] == current_user.id), None)
    
    # ========== FIX: Return 400 for duplicate application (instead of 200) ==========
    if existing:
        raise HTTPException(status_code=400, detail="Already applied for this job")
    # ==============================================================================
    
    applications_db.append({
        "job_id": application.job_id,
        "student_id": current_user.id,
        "student_name": current_user.full_name,
        "message": application.message,
        "applied_at": datetime.now().isoformat()
    })
    
    job["applicants_count"] = job.get("applicants_count", 0) + 1
    
    return {"success": True, "message": "Application submitted successfully"}


@router.get("/my-jobs")
def get_my_posted_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get jobs posted by current user"""
    
    my_jobs = [j for j in jobs_db if j["posted_by_id"] == current_user.id]
    return {"jobs": my_jobs}


@router.get("/my-applications")
def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get jobs applied by current student"""
    
    my_apps = [a for a in applications_db if a["student_id"] == current_user.id]
    return {"applications": my_apps}


@router.post("/activate/{job_id}")
def activate_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate job after payment (₹99 platform fee)"""
    
    job = next((j for j in jobs_db if j["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["posted_by_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    job["payment_status"] = "paid"
    job["is_active"] = True
    
    # Generate payment link (₹99)
    upi_id = "campuscentral@okhdfcbank"
    amount = 99
    
    return {
        "success": True,
        "message": "Job activated!",
        "payment_link": f"upi://pay?pa={upi_id}&pn=Campus%20Central&am={amount}&cu=INR",
        "amount": amount
    }


@router.get("/stats")
def get_marriage_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    
    active_jobs = len([j for j in jobs_db if j.get("is_active") and j.get("payment_status") == "paid"])
    total_applications = len(applications_db)
    registered_students = len(student_profiles_db)
    
    return {
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "registered_students": registered_students,
        "average_pay": 500
    }