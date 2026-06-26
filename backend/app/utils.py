# utils.py - Complete file with TEST MODE for 1-6 rupees
# Phase 1 (June 18, 2026): Initial utility functions.
# Phase 2 (June 19, 2026): Added TEST_MODE for lucky number game.
# Phase 3 (June 25, 2026): Added photo and friends serialization.
# Phase 4 (June 26, 2026): ENHANCED - Added logging instead of print statements.
#                         Better error handling for JSON operations.
#                         Added validation for photo operations.
#                         Added Azure Blob Storage preparation.

import random
import uuid
import json
import os
import base64
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from .config import settings

# ============================================================
# LOGGING SETUP
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# LUCKY NUMBER GENERATION
# ============================================================
def generate_lucky_numbers(friends: List[str], group_type: str) -> Dict[str, Any]:
    """
    Generate random points for each friend and find the lowest.
    
    Args:
        friends: List of friend names
        group_type: "teacher" or "celebration"
    
    Returns:
        Dictionary with friends_points, contribution, lucky_friend, label
    """
    # Set point range based on group type
    if group_type == "teacher":
        # 🔧 TEST MODE: 1-6 (change back to 18-81 for production)
        # Check if TEST_MODE is enabled and use 1-6 range
        if settings.TEST_MODE:
            min_points = 1
            max_points = 6
            logger.info(f"🧪 TEST MODE: Teacher lucky range = 1-6")
        else:
            min_points = settings.TEACHER_MIN_POINTS
            max_points = settings.TEACHER_MAX_POINTS
    else:  # celebration
        min_points = settings.CELEBRATION_MIN_POINTS
        max_points = settings.CELEBRATION_MAX_POINTS
    
    # Generate random points for each friend
    friends_with_points = []
    for friend in friends:
        points = random.randint(min_points, max_points)
        friends_with_points.append({
            "name": friend,
            "points": points
        })
    
    # Find the lowest points
    min_points_value = min(f["points"] for f in friends_with_points)
    lucky_friend_obj = next(f for f in friends_with_points if f["points"] == min_points_value)
    
    # Determine label based on points
    if min_points_value <= settings.ULTRA_LUCKY_MAX:
        label = "ULTRA LUCKY! 👑"
    elif min_points_value <= settings.LUCKIER_MAX:
        label = "LUCKIER! 🌟"
    else:
        label = "LUCKY! 🍀"
    
    return {
        "friends_with_points": friends_with_points,
        "contribution": min_points_value,
        "lucky_friend": lucky_friend_obj["name"],
        "label": label,
        "message": f"🎉 {lucky_friend_obj['name']} got {min_points_value} points! Your contribution: {min_points_value} points"
    }


def generate_group_id() -> str:
    """Generate a unique group ID for sharing"""
    return f"grp_{uuid.uuid4().hex[:12]}"


def get_luck_label_from_points(points: int) -> str:
    """Get the label for a given points value"""
    if points <= settings.ULTRA_LUCKY_MAX:
        return "ULTRA LUCKY! 👑"
    elif points <= settings.LUCKIER_MAX:
        return "LUCKIER! 🌟"
    else:
        return "LUCKY! 🍀"


def validate_friends_count(friends: List[str]) -> Tuple[bool, str]:
    """Validate friend count is between 3 and 9"""
    if len(friends) < 3:
        return False, "Please add at least 3 friends"
    if len(friends) > 9:
        return False, "Maximum 9 friends allowed"
    return True, ""


# ============================================================
# PHOTO OPERATIONS (Local Storage - For Azure Blob migration)
# ============================================================
def save_photo(base64_string: str, folder: str = "groups") -> str:
    """
    Save a base64 encoded photo to disk and return the file path.
    
    ✅ ENHANCED: Added validation, error handling, and logging.
    Note: In production, use Azure Blob Storage instead of local disk.
    """
    if not base64_string:
        logger.warning("⚠️ Empty base64 string provided for photo save")
        return ""
    
    try:
        # Create directory if not exists
        upload_dir = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(upload_dir, filename)
        
        # Decode and save
        if base64_string.startswith("data:image"):
            # Extract base64 part after comma
            base64_string = base64_string.split(",")[1]
        
        image_data = base64.b64decode(base64_string)
        
        # ✅ Validate image size
        if len(image_data) > settings.MAX_UPLOAD_SIZE:
            logger.error(f"❌ Image too large: {len(image_data)} bytes (max: {settings.MAX_UPLOAD_SIZE})")
            return ""
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        logger.info(f"✅ Photo saved: {filepath}")
        # Return relative path
        return f"/{upload_dir}/{filename}"
        
    except base64.binascii.Error as e:
        logger.error(f"❌ Invalid base64 string: {e}")
        return ""
    except IOError as e:
        logger.error(f"❌ Failed to save photo: {e}")
        return ""
    except Exception as e:
        logger.error(f"❌ Unexpected error saving photo: {e}")
        return ""


def validate_photo_size(base64_string: str) -> bool:
    """
    Validate photo size is within limit.
    
    ✅ ENHANCED: Added better error handling.
    """
    if not base64_string:
        return False
    
    try:
        if base64_string.startswith("data:image"):
            base64_string = base64_string.split(",")[1]
        
        # Approximate size: base64 length * 0.75
        approx_size = len(base64_string) * 0.75
        return approx_size <= settings.MAX_UPLOAD_SIZE
        
    except Exception as e:
        logger.error(f"❌ Error validating photo size: {e}")
        return False


# ============================================================
# ✅ ADDED: AZURE BLOB STORAGE PREPARATION
# ============================================================
def get_blob_connection_string() -> str:
    """
    Get Azure Blob Storage connection string from settings.
    Returns empty string if not configured.
    """
    try:
        from app.config import settings
        # This would be fetched from Key Vault in production
        return os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    except Exception as e:
        logger.error(f"❌ Error getting blob connection string: {e}")
        return ""


def upload_to_blob(file_path: str, container_name: str = "photos") -> str:
    """
    ✅ NEW: Upload a file to Azure Blob Storage.
    This is a placeholder for future Azure Blob integration.
    """
    try:
        from azure.storage.blob import BlobServiceClient
        
        conn_str = get_blob_connection_string()
        if not conn_str:
            logger.warning("⚠️ Azure Storage not configured, using local storage")
            return file_path
        
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=os.path.basename(file_path)
        )
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        
        url = blob_client.url
        logger.info(f"✅ File uploaded to Azure Blob: {url}")
        return url
        
    except ImportError:
        logger.warning("⚠️ Azure Storage SDK not installed, using local storage")
        return file_path
    except Exception as e:
        logger.error(f"❌ Error uploading to blob: {e}")
        return file_path


# ============================================================
# SERIALIZATION HELPERS (with error handling)
# ============================================================
def serialize_photos(photos: List[str]) -> str:
    """Serialize photo list to JSON string with error handling"""
    if not photos:
        return "[]"
    try:
        return json.dumps(photos)
    except Exception as e:
        logger.error(f"❌ Error serializing photos: {e}")
        return "[]"


def deserialize_photos(photos_json: str) -> List[str]:
    """Deserialize JSON string to photo list with error handling"""
    if not photos_json:
        return []
    try:
        return json.loads(photos_json)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error deserializing photos: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Unexpected error deserializing photos: {e}")
        return []


def serialize_friends(friends_with_points: List[Dict]) -> str:
    """Serialize friends with points to JSON string with error handling"""
    if not friends_with_points:
        return "[]"
    try:
        return json.dumps(friends_with_points)
    except Exception as e:
        logger.error(f"❌ Error serializing friends: {e}")
        return "[]"


def deserialize_friends(friends_json: str) -> List[Dict]:
    """Deserialize JSON string to friends list with error handling"""
    if not friends_json:
        return []
    try:
        return json.loads(friends_json)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error deserializing friends: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Unexpected error deserializing friends: {e}")
        return []


# ============================================================
# EVENT COUNTDOWN (with better error handling)
# ============================================================
def calculate_next_event_countdown(event_date: str) -> str:
    """Calculate days until event with better error handling"""
    if not event_date:
        return "Date TBD"
    
    try:
        # Try multiple date formats
        formats = ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]
        event_date_obj = None
        
        for fmt in formats:
            try:
                event_date_obj = datetime.strptime(event_date, fmt)
                break
            except ValueError:
                continue
        
        if not event_date_obj:
            return "Date TBD"
        
        today = datetime.now().date()
        delta = (event_date_obj.date() - today).days
        
        if delta < 0:
            return "Past event"
        elif delta == 0:
            return "Today! 🎉"
        elif delta == 1:
            return "Tomorrow"
        else:
            return f"{delta} days"
            
    except Exception as e:
        logger.error(f"❌ Error calculating countdown: {e}")
        return "Date TBD"


# ============================================================
# ✅ ADDED: ADDITIONAL UTILITY FUNCTIONS
# ============================================================
def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate a string to a maximum length"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    dangerous = ["<", ">", "&", "'", '"']
    for char in dangerous:
        text = text.replace(char, "")
    return text.strip()


def is_valid_whatsapp(whatsapp: str) -> bool:
    """Validate WhatsApp number format"""
    if not whatsapp:
        return False
    import re
    return bool(re.match(r'^[6-9]\d{9}$', whatsapp))


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    import re
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))