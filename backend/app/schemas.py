# app/schemas.py - COMPLETE FILE WITH VIDEO_URL
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ============ AUTH SCHEMAS ============
class UserSignup(BaseModel):
    full_name: str
    email: EmailStr
    whatsapp: str
    password: str
    role: str = "student"
    hometown: Optional[str] = None
    district: Optional[str] = None
    college: Optional[str] = None
    gender: Optional[str] = None
    hobbies: Optional[str] = None
    course: Optional[str] = None
    specialization: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: Optional[str] = None
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ============ WHATSAPP SIGNUP SCHEMAS ============
class WhatsAppSignup(BaseModel):
    whatsapp: str
    full_name: str
    course: Optional[str] = None
    photo: Optional[str] = None
    voice_used: bool = False

class WhatsAppLogin(BaseModel):
    whatsapp: str
    password: str

# ============ OTP SCHEMAS ============
class OTPRequest(BaseModel):
    whatsapp: str

class OTPVerify(BaseModel):
    whatsapp: str
    otp: str
    # ============ TEACHER GROUP SCHEMAS ============
class FriendWithPoints(BaseModel):
    name: str
    points: int

class TeacherGroupCreate(BaseModel):
    teacher_name: str
    college: Optional[str] = None
    district: Optional[str] = None
    event_date: Optional[str] = None
    venue: Optional[str] = None
    pet_names: Optional[str] = None
    secret_code: Optional[str] = None
    memory: Optional[str] = None
    bring: Optional[str] = None
    dress_code: Optional[str] = None
    surprise: Optional[str] = None
    note: Optional[str] = None
    photos: Optional[List[str]] = None

class TeacherLuckyGameSubmit(BaseModel):
    group_id: str
    friends: List[str]
    contribution_points: int
    lucky_friend: str

class TeacherGroupResponse(BaseModel):
    id: int
    group_id: str
    teacher_name: str
    college: Optional[str]
    district: Optional[str]
    event_date: Optional[str]
    venue: Optional[str]
    status: str
    contribution_points: int
    lucky_friend: str
    member_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

# ============ CELEBRATION GROUP SCHEMAS ============
class CelebrationGroupCreate(BaseModel):
    title: str
    location: Optional[str] = None
    district: Optional[str] = None
    event_date: Optional[str] = None
    venue: Optional[str] = None
    pet_names: Optional[str] = None
    secret_code: Optional[str] = None
    memory: Optional[str] = None
    bring: Optional[str] = None
    dress_code: Optional[str] = None
    surprise: Optional[str] = None
    note: Optional[str] = None
    photos: Optional[List[str]] = None

class CelebrationLuckyGameSubmit(BaseModel):
    group_id: str
    friends: List[str]
    contribution_points: int
    lucky_friend: str

class CelebrationGroupResponse(BaseModel):
    id: int
    group_id: str
    title: str
    location: Optional[str]
    district: Optional[str]
    event_date: Optional[str]
    venue: Optional[str]
    status: str
    contribution_points: int
    lucky_friend: str
    member_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

# ============ LUCKY NUMBER GAME ============
class LuckyGameRequest(BaseModel):
    friends: List[str]
    group_type: str  # "teacher" or "celebration"

class LuckyGameResponse(BaseModel):
    success: bool
    friends_with_points: List[dict]
    contribution: int
    lucky_friend: str
    label: str
    message: str
    # ============ GROUP SEARCH ============
class GroupSearchResponse(BaseModel):
    id: int
    group_id: str
    type: str
    name: str
    location: str
    district: str
    event_date: Optional[str]
    member_count: int
    status: str

# ============ DASHBOARD ============
class DashboardGroup(BaseModel):
    group_id: str
    name: str
    type: str
    status: str
    member_count: int
    event_date: Optional[str]
    is_organizer: bool
    contribution_points: Optional[int]

class DashboardResponse(BaseModel):
    total_groups: int
    active_groups: int
    pending_groups: int
    groups: List[DashboardGroup]

# ============ SUCCESS STORIES ============
class StoryCreate(BaseModel):
    story_text: str
    author_name: str

class StoryResponse(BaseModel):
    id: int
    story_text: str
    author_name: str
    created_at: datetime

    class Config:
        from_attributes = True

# ============ MESSAGES ============
class MessageCreate(BaseModel):
    message: str

class MessageResponse(BaseModel):
    id: int
    user_name: str
    message: str
    sent_at: datetime

# ============ JOIN GROUP ============
class JoinGroupRequest(BaseModel):
    group_id: str
    group_type: str

# ============ PUBLIC GROUP INFO (For join.html - No Auth Required) ============
class PublicGroupResponse(BaseModel):
    """
    Public group information schema - No authentication required.
    Used by join.html to display group details before user logs in.
    """
    success: bool = True
    type: str  # "teacher" or "celebration"
    group_id: str
    name: str
    member_count: int
    status: str
    is_active: bool
    event_date: Optional[str] = None
    venue: Optional[str] = None
    college: Optional[str] = None  # for teacher groups
    location: Optional[str] = None  # for celebration groups
    district: Optional[str] = None
    pet_names: Optional[str] = None
    secret_code: Optional[str] = None
    memory: Optional[str] = None
    bring: Optional[str] = None
    dress_code: Optional[str] = None
    surprise: Optional[str] = None
    note: Optional[str] = None
    photos: Optional[List[str]] = None
    contribution_points: Optional[int] = None
    lucky_friend: Optional[str] = None

    class Config:
        from_attributes = True

# ============ SOCIAL POSTS (Find My Friend / Mood & Memory) ============
class SocialPostCreate(BaseModel):
    """Schema for creating a social post (friend search or mood/memory)"""
    college: str
    batch: Optional[str] = None
    message: str
    title: str = ""                    # For Mood & Memory
    category: str = "mood"             # "mood" or "memory"
    privacy: str = "public"
    anonymous: bool = False
    photo: Optional[str] = None


class SocialPostResponse(BaseModel):
    """Schema for returning a social post with video support"""
    id: int
    user_id: int
    user_name: str
    college: str
    batch: Optional[str] = None
    message: str
    title: str                         # For Mood & Memory
    category: str                      # "mood" or "memory"
    photo: Optional[str] = None
    video_url: Optional[str] = None    # NEW: For uploaded videos
    privacy: str
    anonymous: bool
    likes_count: int
    created_at: datetime
    comments: List["SocialCommentResponse"] = []

    class Config:
        from_attributes = True


class SocialCommentCreate(BaseModel):
    """Schema for creating a comment on a social post"""
    text: str


class SocialCommentResponse(BaseModel):
    """Schema for returning a comment"""
    id: int
    user_id: int
    user_name: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class SocialLikeResponse(BaseModel):
    """Schema for like response"""
    liked: bool
    likes_count: int


# ============ TRACK 3: FIND MY FRIEND SCHEMAS ============
class FriendStoryCreate(BaseModel):
    """Schema for creating a new friend story"""
    story_text: str
    contact_email: Optional[str] = None
    contact_mobile: Optional[str] = None
    hint_questions: Optional[List[dict]] = None  # [{question: str, answer: str}]

class FriendStoryResponse(BaseModel):
    """Schema for returning a friend story (without contact info)"""
    id: int
    user_id: int
    user_name: str
    story_text: str
    extracted_names: Optional[str] = None
    extracted_colleges: Optional[str] = None
    extracted_batches: Optional[str] = None
    extracted_nicknames: Optional[str] = None
    hint_questions: Optional[List[dict]] = None  # Questions only (answers hidden)
    created_at: datetime
    match_score: Optional[float] = None  # For search results

    class Config:
        from_attributes = True

class FriendStorySearchRequest(BaseModel):
    """Schema for searching friend stories"""
    query: str  # The search text (e.g., "Priya from RVCE 2019")
    limit: int = 20

class FriendStoryRevealRequest(BaseModel):
    """Schema for revealing contact info after answering hints"""
    story_id: int
    answers: List[str]  # Answers to hint questions in order

class FriendStoryRevealResponse(BaseModel):
    """Schema for revealing contact info"""
    success: bool
    contact_email: Optional[str] = None
    contact_mobile: Optional[str] = None
    message: str

class FriendStoryDeleteRequest(BaseModel):
    """Schema for deleting a story"""
    story_id: int


# ============ Forward references for SocialPostResponse ============
SocialPostResponse.model_rebuild()