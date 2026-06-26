"""
app/models.py - COMPLETE FILE WITH VIDEO_URL + RAZORPAY PAYMENT COLUMNS

Phase 1 (June 18, 2026): Initial models for all core entities.
Phase 2 (June 19, 2026): Added SocialPost, SocialComment, SocialLike models.
Phase 3 (June 25, 2026): Added video_url to SocialPost for video uploads.
                         Added Razorpay payment columns to Payment model.
Phase 4 (June 26, 2026): ENHANCED - Added __table_args__ for Azure SQL compatibility.
                         Added indexes for frequently queried columns.
                         Added cascading deletes for better data integrity.
                         Added string length constraints for Azure SQL.
                         FIXED: Indentation error for all classes.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    whatsapp = Column(String(20), nullable=False, index=True)
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
    
    __table_args__ = (
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_whatsapp', 'whatsapp'),
        Index('idx_users_college', 'college'),
    )
    
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
    status = Column(String(50), default="pending", index=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_public = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_teacher_groups_status', 'status'),
        Index('idx_teacher_groups_created_at', 'created_at'),
        Index('idx_teacher_groups_district', 'district'),
    )
    
    members = relationship("GroupMember", back_populates="teacher_group")


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_otp_expires_at', 'expires_at'),
        Index('idx_otp_whatsapp_expires', 'whatsapp', 'expires_at'),
    )


class FriendStory(Base):
    __tablename__ = "friend_stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
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
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_friend_stories_is_active', 'is_active'),
        Index('idx_friend_stories_created_at', 'created_at'),
        Index('idx_friend_stories_user_id', 'user_id'),
    )


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
    status = Column(String(50), default="pending", index=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_public = Column(Boolean, default=True)
    
    __table_args__ = (
        Index('idx_celebration_groups_status', 'status'),
        Index('idx_celebration_groups_created_at', 'created_at'),
        Index('idx_celebration_groups_district', 'district'),
    )
    
    members = relationship("GroupMember", back_populates="celebration_group")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_type = Column(String(20), nullable=False)
    teacher_group_id = Column(Integer, ForeignKey("teacher_groups.id", ondelete="CASCADE"), nullable=True)
    celebration_group_id = Column(Integer, ForeignKey("celebration_groups.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'teacher_group_id', name='unique_user_teacher_group'),
        UniqueConstraint('user_id', 'celebration_group_id', name='unique_user_celebration_group'),
        Index('idx_group_members_user_id', 'user_id'),
        Index('idx_group_members_group_type', 'group_type'),
        Index('idx_group_members_teacher_group_id', 'teacher_group_id'),
        Index('idx_group_members_celebration_group_id', 'celebration_group_id'),
    )
    
    user = relationship("User", back_populates="memberships")
    teacher_group = relationship("TeacherGroup", back_populates="members")
    celebration_group = relationship("CelebrationGroup", back_populates="members")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    group_type = Column(String(20), nullable=False)
    teacher_group_id = Column(Integer, ForeignKey("teacher_groups.id", ondelete="CASCADE"), nullable=True)
    celebration_group_id = Column(Integer, ForeignKey("celebration_groups.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_messages_sent_at', 'sent_at'),
        Index('idx_messages_teacher_group_id', 'teacher_group_id'),
        Index('idx_messages_celebration_group_id', 'celebration_group_id'),
    )
    
    user = relationship("User", back_populates="messages")


# ============ UPDATED PAYMENT MODEL WITH RAZORPAY COLUMNS ============
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    group_type = Column(String(20), nullable=False)
    teacher_group_id = Column(Integer, ForeignKey("teacher_groups.id", ondelete="SET NULL"), nullable=True)
    celebration_group_id = Column(Integer, ForeignKey("celebration_groups.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", index=True)
    
    # ✅ RAZORPAY COLUMNS
    razorpay_order_id = Column(String(255), nullable=True, index=True)
    razorpay_payment_id = Column(String(255), nullable=True, index=True)
    razorpay_signature = Column(String(255), nullable=True)
    
    # ✅ UPI (kept for backward compatibility)
    upi_txn_id = Column(String(255), nullable=True)
    
    # ✅ Timestamps
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_payments_status', 'status'),
        Index('idx_payments_razorpay_order_id', 'razorpay_order_id'),
        Index('idx_payments_razorpay_payment_id', 'razorpay_payment_id'),
        Index('idx_payments_created_at', 'created_at'),
        Index('idx_payments_user_id', 'user_id'),
    )
    
    # Relationships
    user = relationship("User")
    teacher_group = relationship("TeacherGroup")
    celebration_group = relationship("CelebrationGroup")


class SuccessStory(Base):
    __tablename__ = "success_stories"

    id = Column(Integer, primary_key=True, index=True)
    story_text = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=False)
    is_approved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_success_stories_is_approved', 'is_approved'),
        Index('idx_success_stories_created_at', 'created_at'),
    )


# ============ SOCIAL POSTS (Public feed – Find My Friend / Mood & Memory) ============
class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_name = Column(String(255), nullable=False)
    college = Column(String(255), nullable=False)
    batch = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    photo = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=True)
    privacy = Column(String(20), default="public")
    anonymous = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # For Mood & Memory page
    title = Column(String(255), nullable=False, default="")
    category = Column(String(20), nullable=False, default="mood")
    
    __table_args__ = (
        Index('idx_social_posts_created_at', 'created_at'),
        Index('idx_social_posts_user_id', 'user_id'),
        Index('idx_social_posts_college', 'college'),
        Index('idx_social_posts_category', 'category'),
        Index('idx_social_posts_privacy', 'privacy'),
    )

    user = relationship("User", backref="social_posts")
    comments = relationship("SocialComment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("SocialLike", back_populates="post", cascade="all, delete-orphan")


class SocialComment(Base):
    __tablename__ = "social_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_name = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_social_comments_post_id', 'post_id'),
        Index('idx_social_comments_created_at', 'created_at'),
    )

    post = relationship("SocialPost", back_populates="comments")
    user = relationship("User")


class SocialLike(Base):
    __tablename__ = "social_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='unique_post_user_like'),
        Index('idx_social_likes_post_id', 'post_id'),
        Index('idx_social_likes_user_id', 'user_id'),
    )

    post = relationship("SocialPost", back_populates="likes")
    user = relationship("User")


# ============ CONNECTION REQUESTS ============
class ConnectionRequest(Base):
    __tablename__ = "connection_requests"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_connection_requests_status', 'status'),
        Index('idx_connection_requests_from_user_id', 'from_user_id'),
        Index('idx_connection_requests_to_user_id', 'to_user_id'),
        Index('idx_connection_requests_created_at', 'created_at'),
    )

    from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_requests")
    to_user = relationship("User", foreign_keys=[to_user_id], backref="received_requests")