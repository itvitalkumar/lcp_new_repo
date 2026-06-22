# Placeholder - Code will be added
import random
import uuid
import json
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
from .config import settings

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


def save_photo(base64_string: str, folder: str = "groups") -> str:
    """
    Save a base64 encoded photo to disk and return the file path.
    In production, use Azure Blob Storage instead.
    """
    import base64
    
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
    with open(filepath, "wb") as f:
        f.write(image_data)
    
    # Return relative path
    return f"/{upload_dir}/{filename}"


def validate_photo_size(base64_string: str) -> bool:
    """Validate photo size is within limit"""
    import base64
    if base64_string.startswith("data:image"):
        base64_string = base64_string.split(",")[1]
    
    # Approximate size: base64 length * 0.75
    approx_size = len(base64_string) * 0.75
    return approx_size <= settings.MAX_UPLOAD_SIZE


def serialize_photos(photos: List[str]) -> str:
    """Serialize photo list to JSON string"""
    return json.dumps(photos)


def deserialize_photos(photos_json: str) -> List[str]:
    """Deserialize JSON string to photo list"""
    if not photos_json:
        return []
    return json.loads(photos_json)


def serialize_friends(friends_with_points: List[Dict]) -> str:
    """Serialize friends with points to JSON string"""
    return json.dumps(friends_with_points)


def deserialize_friends(friends_json: str) -> List[Dict]:
    """Deserialize JSON string to friends list"""
    if not friends_json:
        return []
    return json.loads(friends_json)


def calculate_next_event_countdown(event_date: str) -> str:
    """Calculate days until event"""
    if not event_date:
        return "Date TBD"
    
    try:
        event_date_obj = datetime.strptime(event_date, "%Y-%m-%d")
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
    except:
        return "Date TBD"