"""
app/schemas.py - COMPLETE FILE WITH VIDEO_URL

Phase 1 (June 18, 2026): Initial schemas for all core entities.
Phase 2 (June 19, 2026): Added WhatsApp and OTP schemas.
Phase 3 (June 25, 2026): Added video_url to SocialPostResponse.
                         Added Razorpay payment schemas.
Phase 4 (June 26, 2026): ENHANCED - Added validation constraints.
                         Added missing schemas for payment verification.
                         Added example values for better API documentation.
                         Added field descriptions for Swagger UI.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
import re


# ============================================================
# AUTH SCHEMAS
# ============================================================
class UserSignup(BaseModel):
    """Schema for user registration."""
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of the user")
    email: EmailStr = Field(..., description="Valid email address")
    whatsapp: str = Field(..., pattern=r'^[6-9]\d{9}$', description="10-digit Indian WhatsApp number")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    role: str = Field("student", description="User role: student, teacher, admin")
    hometown: Optional[str] = Field(None, max_length=255)
    district: Optional[str] = Field(None, max_length=100)
    college: Optional[str] = Field(None, max_length=255)
    gender: Optional[str] = Field(None, max_length=20)
    hobbies: Optional[str] = None
    course: Optional[str] = Field(None, max_length=100)
    specialization: Optional[str] = Field(None, max_length=100)
    
    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        """Validate WhatsApp number format."""
        if not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('WhatsApp number must be 10 digits starting with 6,7,8,9')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: Optional[str] = None
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================
# WHATSAPP SIGNUP SCHEMAS
# ============================================================
class WhatsAppSignup(BaseModel):
    """Schema for WhatsApp-based signup."""
    whatsapp: str = Field(..., pattern=r'^[6-9]\d{9}$', description="10-digit Indian WhatsApp number")
    full_name: str = Field(..., min_length=2, max_length=255)
    course: Optional[str] = Field(None, max_length=100)
    photo: Optional[str] = None
    voice_used: bool = False
    
    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        if not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('WhatsApp number must be 10 digits starting with 6,7,8,9')
        return v


class WhatsAppLogin(BaseModel):
    """Schema for WhatsApp-based login."""
    whatsapp: str = Field(..., pattern=r'^[6-9]\d{9}$')
    password: str = Field(..., min_length=6)


# ============================================================
# OTP SCHEMAS
# ============================================================
class OTPRequest(BaseModel):
    """Schema for requesting OTP."""
    whatsapp: str = Field(..., pattern=r'^[6-9]\d{9}$')
    
    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        if not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('WhatsApp number must be 10 digits starting with 6,7,8,9')
        return v


class OTPVerify(BaseModel):
    """Schema for verifying OTP."""
    whatsapp: str = Field(..., pattern=r'^[6-9]\d{9}$')
    otp: str = Field(..., pattern=r'^\d{6}$', description="6-digit OTP")
    
    @validator('whatsapp')
    def validate_whatsapp(cls, v):
        if not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('WhatsApp number must be 10 digits starting with 6,7,8,9')
        return v


# ============================================================
# TEACHER GROUP SCHEMAS
# ============================================================
class FriendWithPoints(BaseModel):
    """Schema for friend with lucky points."""
    name: str
    points: int


class TeacherGroupCreate(BaseModel):
    """Schema for creating a teacher group."""
    teacher_name: str = Field(..., min_length=1, max_length=255)
    college: Optional[str] = Field(None, max_length=255)
    district: Optional[str] = Field(None, max_length=100)
    event_date: Optional[str] = Field(None, max_length=50)
    venue: Optional[str] = Field(None, max_length=255)
    pet_names: Optional[str] = Field(None, max_length=255)
    secret_code: Optional[str] = Field(None, max_length=100)
    memory: Optional[str] = None
    bring: Optional[str] = Field(None, max_length=255)
    dress_code: Optional[str] = Field(None, max_length=255)
    surprise: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None
    photos: Optional[List[str]] = None


class TeacherLuckyGameSubmit(BaseModel):
    """Schema for submitting teacher lucky game result."""
    group_id: str = Field(..., min_length=1)
    friends: List[str] = Field(..., min_items=3, max_items=9)
    contribution_points: int = Field(..., ge=1, le=100)
    lucky_friend: str = Field(..., min_length=1)


class TeacherGroupResponse(BaseModel):
    """Schema for teacher group response."""
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


# ============================================================
# CELEBRATION GROUP SCHEMAS
# ============================================================
class CelebrationGroupCreate(BaseModel):
    """Schema for creating a celebration group."""
    title: str = Field(..., min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    district: Optional[str] = Field(None, max_length=100)
    event_date: Optional[str] = Field(None, max_length=50)
    venue: Optional[str] = Field(None, max_length=255)
    pet_names: Optional[str] = Field(None, max_length=255)
    secret_code: Optional[str] = Field(None, max_length=100)
    memory: Optional[str] = None
    bring: Optional[str] = Field(None, max_length=255)
    dress_code: Optional[str] = Field(None, max_length=255)
    surprise: Optional[str] = Field(None, max_length=255)
    note: Optional[str] = None
    photos: Optional[List[str]] = None


class CelebrationLuckyGameSubmit(BaseModel):
    """Schema for submitting celebration lucky game result."""
    group_id: str = Field(..., min_length=1)
    friends: List[str] = Field(..., min_items=3, max_items=9)
    contribution_points: int = Field(..., ge=1, le=100)
    lucky_friend: str = Field(..., min_length=1)


class CelebrationGroupResponse(BaseModel):
    """Schema for celebration group response."""
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


# ============================================================
# LUCKY NUMBER GAME SCHEMAS
# ============================================================
class LuckyGameRequest(BaseModel):
    """Schema for lucky number game request."""
    friends: List[str] = Field(..., min_items=3, max_items=9)
    group_type: str = Field(..., description="teacher or celebration")


class LuckyGameResponse(BaseModel):
    """Schema for lucky number game response."""
    success: bool
    friends_with_points: List[dict]
    contribution: int
    lucky_friend: str
    label: str
    message: str
    # ============================================================
# GROUP SEARCH SCHEMAS
# ============================================================
class GroupSearchResponse(BaseModel):
    """Schema for group search response."""
    id: int
    group_id: str
    type: str
    name: str
    location: str
    district: str
    event_date: Optional[str]
    member_count: int
    status: str


# ============================================================
# DASHBOARD SCHEMAS
# ============================================================
class DashboardGroup(BaseModel):
    """Schema for dashboard group item."""
    group_id: str
    name: str
    type: str
    status: str
    member_count: int
    event_date: Optional[str]
    is_organizer: bool
    contribution_points: Optional[int]


class DashboardResponse(BaseModel):
    """Schema for dashboard response."""
    total_groups: int
    active_groups: int
    pending_groups: int
    groups: List[DashboardGroup]


# ============================================================
# SUCCESS STORIES SCHEMAS
# ============================================================
class StoryCreate(BaseModel):
    """Schema for creating a success story."""
    story_text: str = Field(..., min_length=10)
    author_name: str = Field(..., min_length=2, max_length=255)


class StoryResponse(BaseModel):
    """Schema for success story response."""
    id: int
    story_text: str
    author_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# MESSAGES SCHEMAS
# ============================================================
class MessageCreate(BaseModel):
    """Schema for creating a message."""
    message: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: int
    user_name: str
    message: str
    sent_at: datetime


# ============================================================
# JOIN GROUP SCHEMAS
# ============================================================
class JoinGroupRequest(BaseModel):
    """Schema for joining a group."""
    group_id: str = Field(..., min_length=1)
    group_type: str = Field(..., description="teacher or celebration")


# ============================================================
# PUBLIC GROUP INFO (For join.html - No Auth Required)
# ============================================================
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


# ============================================================
# ✅ ADDED: PAYMENT SCHEMAS
# ============================================================
class PaymentCreateOrderRequest(BaseModel):
    """Schema for creating a Razorpay order."""
    amount: int = Field(..., gt=0, description="Amount in rupees")
    group_id: str = Field(..., min_length=1)
    group_type: str = Field(..., description="teacher or celebration")


class PaymentCreateOrderResponse(BaseModel):
    """Schema for Razorpay order creation response."""
    success: bool
    order_id: str
    amount: int
    key: str
    group_id: str
    group_type: str


class PaymentVerifyRequest(BaseModel):
    """Schema for verifying Razorpay payment."""
    razorpay_payment_id: str = Field(..., min_length=1)
    razorpay_order_id: str = Field(..., min_length=1)
    razorpay_signature: str = Field(..., min_length=1)
    group_id: str = Field(..., min_length=1)
    group_type: str = Field(..., description="teacher or celebration")


class PaymentVerifyResponse(BaseModel):
    """Schema for payment verification response."""
    success: bool
    message: str
    group_id: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    """Schema for payment status response."""
    status: str
    amount: int
    paid_at: Optional[datetime] = None


# ============================================================
# SOCIAL POSTS (Find My Friend / Mood & Memory)
# ============================================================
class SocialPostCreate(BaseModel):
    """Schema for creating a social post (friend search or mood/memory)"""
    college: str = Field(..., max_length=255)
    batch: Optional[str] = Field(None, max_length=50)
    message: str = Field(..., min_length=1)
    title: str = Field("", max_length=255)  # For Mood & Memory
    category: str = Field("mood", description="mood or memory")
    privacy: str = Field("public", description="public or private")
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
    title: str  # For Mood & Memory
    category: str  # "mood" or "memory"
    photo: Optional[str] = None
    video_url: Optional[str] = None  # NEW: For uploaded videos
    privacy: str
    anonymous: bool
    likes_count: int
    created_at: datetime
    comments: List["SocialCommentResponse"] = []

    class Config:
        from_attributes = True


class SocialCommentCreate(BaseModel):
    """Schema for creating a comment on a social post"""
    text: str = Field(..., min_length=1)


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


# ============================================================
# FIND MY FRIEND SCHEMAS
# ============================================================
class FriendStoryCreate(BaseModel):
    """Schema for creating a new friend story"""
    story_text: str = Field(..., min_length=10)
    contact_email: Optional[EmailStr] = None
    contact_mobile: Optional[str] = Field(None, pattern=r'^[6-9]\d{9}$')
    hint_questions: Optional[List[dict]] = None  # [{question: str, answer: str}]
    
    @validator('contact_mobile')
    def validate_contact_mobile(cls, v):
        if v and not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('Contact mobile must be 10 digits starting with 6,7,8,9')
        return v


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
    query: str = Field(..., min_length=1)
    limit: int = Field(20, ge=1, le=100)


class FriendStoryRevealRequest(BaseModel):
    """Schema for revealing contact info after answering hints"""
    story_id: int
    answers: List[str] = Field(..., min_items=1)


class FriendStoryRevealResponse(BaseModel):
    """Schema for revealing contact info"""
    success: bool
    contact_email: Optional[str] = None
    contact_mobile: Optional[str] = None
    message: str


class FriendStoryDeleteRequest(BaseModel):
    """Schema for deleting a story"""
    story_id: int


# ============================================================
# ✅ ADDED: RAZORPAY WEBHOOK SCHEMA
# ============================================================
class RazorpayWebhookPayload(BaseModel):
    """Schema for Razorpay webhook payload."""
    event: str
    payload: dict


# ============================================================
# Forward references for SocialPostResponse
# ============================================================
SocialPostResponse.model_rebuild()