# app/models.py - COMPLETE FILE WITH VIDEO_URL + RAZORPAY PAYMENT COLUMNS
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    whatsapp = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="student")
    
    hometown = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    college = Column(String(255), nullable=True)
    gender = Column(String(20), nullable=True)
    hobbies = Column(Text, nullable=True)
    course = Column(String(100), nullable=True)
    specialization = Column(String(100), nullable=True)
    photo = Column(Text, nullable=True)
    voice_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    groups_created = relationship("TeacherGroup", foreign_keys="TeacherGroup.created_by", backref="creator")
    celebration_groups_created = relationship("CelebrationGroup", foreign_keys="CelebrationGroup.created_by", backref="creator")
    memberships = relationship("GroupMember", back_populates="user")
    messages = relationship("Message", back_populates="user")


class TeacherGroup(Base):
    __tablename__ = "teacher_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(100), unique=True, index=True, nullable=False)
    teacher_name = Column(String(255), nullable=False)
    college = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    event_date = Column(String(50), nullable=True)
    venue = Column(String(255), nullable=True)
    pet_names = Column(String(255), nullable=True)
    secret_code = Column(String(100), nullable=True)
    memory = Column(Text, nullable=True)
    bring = Column(String(255), nullable=True)
    dress_code = Column(String(255), nullable=True)
    surprise = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    photos = Column(Text, nullable=True)
    friends_list = Column(Text, nullable=True)
    contribution_points = Column(Integer, nullable=False)
    lucky_friend = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_public = Column(Boolean, default=True)
    
    members = relationship("GroupMember", back_populates="teacher_group")


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
class FriendStory(Base):
    __tablename__ = "friend_stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    story_text = Column(Text, nullable=False)
    story_embedding = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_mobile = Column(String(20), nullable=True)
    hint_questions = Column(Text, nullable=True)
    extracted_names = Column(String(500), nullable=True)
    extracted_colleges = Column(String(500), nullable=True)
    extracted_batches = Column(String(200), nullable=True)
    extracted_nicknames = Column(String(500), nullable=True)
    contact_revealed_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CelebrationGroup(Base):
    __tablename__ = "celebration_groups"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    event_date = Column(String(50), nullable=True)
    venue = Column(String(255), nullable=True)
    pet_names = Column(String(255), nullable=True)
    secret_code = Column(String(100), nullable=True)
    memory = Column(Text, nullable=True)
    bring = Column(String(255), nullable=True)
    dress_code = Column(String(255), nullable=True)
    surprise = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    photos = Column(Text, nullable=True)
    friends_list = Column(Text, nullable=True)
    contribution_points = Column(Integer, nullable=False)
    lucky_friend = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_public = Column(Boolean, default=True)
    
    members = relationship("GroupMember", back_populates="celebration_group")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_type = Column(String(20), nullable=False)
    teacher_group_id = Column(Integer, ForeignKey("teacher_groups.id"), nullable=True)
    celebration_group_id = Column(Integer, ForeignKey("celebration_groups.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20), default="member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'teacher_group_id', name='unique_user_teacher_group'),
        UniqueConstraint('user_id', 'celebration_group_id', name='unique_user_celebration_group'),
    )
    
    user = relationship("User", back_populates="memberships")
    teacher_group = relationship("TeacherGroup", back_populates="members")
    celebration_group = relationship("CelebrationGroup", back_populates="members")
    
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    group_type = Column(String(20), nullable=False)
    teacher_group_id = Column(Integer, ForeignKey("teacher_groups.id"), nullable=True)
    celebration_group_id = Column(Integer, ForeignKey("celebration_groups.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="messages")


# ============ UPDATED PAYMENT MODEL WITH RAZORPAY COLUMNS ============
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    group_type = Column(String(20), nullable=False)
    teacher_group_id = Column(Integer, ForeignKey("teacher_groups.id"), nullable=True)
    celebration_group_id = Column(Integer, ForeignKey("celebration_groups.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")
    
    # ✅ RAZORPAY COLUMNS (ADDED)
    razorpay_order_id = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    razorpay_signature = Column(String(255), nullable=True)
    
    # ✅ UPI (kept for backward compatibility)
    upi_txn_id = Column(String(255), nullable=True)
    
    # ✅ Timestamps
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    teacher_group = relationship("TeacherGroup")
    celebration_group = relationship("CelebrationGroup")
    
class SuccessStory(Base):
    __tablename__ = "success_stories"

    id = Column(Integer, primary_key=True, index=True)
    story_text = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============ SOCIAL POSTS (Public feed – Find My Friend / Mood & Memory) ============
class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_name = Column(String(255), nullable=False)
    college = Column(String(255), nullable=False)
    batch = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    photo = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=True)  # NEW: For uploaded videos
    privacy = Column(String(20), default="public")
    anonymous = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # For Mood & Memory page
    title = Column(String(255), nullable=False, default="")
    category = Column(String(20), nullable=False, default="mood")

    user = relationship("User", backref="social_posts")
    comments = relationship("SocialComment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("SocialLike", back_populates="post", cascade="all, delete-orphan")


class SocialComment(Base):
    __tablename__ = "social_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_name = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("SocialPost", back_populates="comments")
    user = relationship("User")
    
class SocialLike(Base):
    __tablename__ = "social_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint('post_id', 'user_id', name='unique_post_user_like'),)

    post = relationship("SocialPost", back_populates="likes")
    user = relationship("User")


# ============ CONNECTION REQUESTS ============
class ConnectionRequest(Base):
    __tablename__ = "connection_requests"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)

    from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_requests")
    to_user = relationship("User", foreign_keys=[to_user_id], backref="received_requests")