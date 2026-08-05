"""
Announcement endpoints for the High School Management System API
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1000)
    start_date: Optional[date] = None
    expiration_date: date


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    message: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    start_date: Optional[date] = None
    expiration_date: Optional[date] = None


def require_signed_in_user(teacher_username: Optional[str]) -> Dict[str, Any]:
    """Ensure a teacher is signed in before allowing a management action."""
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    return teacher


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return date.fromisoformat(value)


def announcement_is_active(document: Dict[str, Any]) -> bool:
    today = date.today()
    start_date = parse_date(document.get("start_date"))
    expiration_date = parse_date(document.get("expiration_date"))

    if not expiration_date:
        return False

    if start_date and today < start_date:
        return False

    return today <= expiration_date


def serialize_announcement(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document["title"],
        "message": document["message"],
        "start_date": document.get("start_date"),
        "expiration_date": document.get("expiration_date"),
        "created_by": document.get("created_by"),
        "created_by_display_name": document.get("created_by_display_name"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "is_active": announcement_is_active(document)
    }


def announcement_sort_key(document: Dict[str, Any]) -> tuple:
    return (
        0 if document.get("is_active") else 1,
        document.get("expiration_date") or "",
        document.get("start_date") or "",
        document.get("title") or ""
    )


@router.get("")
@router.get("/")
def get_announcements(active_only: bool = False) -> List[Dict[str, Any]]:
    """Return all announcements or only currently active ones."""
    announcements = [serialize_announcement(doc)
                       for doc in announcements_collection.find({})]
    announcements.sort(key=announcement_sort_key)

    if active_only:
        return [announcement for announcement in announcements if announcement["is_active"]]

    return announcements


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Return only active announcements for the public banner."""
    return get_announcements(active_only=True)


@router.post("")
@router.post("/")
def create_announcement(
    announcement: AnnouncementCreate,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement."""
    teacher = require_signed_in_user(teacher_username)

    if announcement.expiration_date < date.today():
        raise HTTPException(
            status_code=400, detail="Expiration date must be today or later")

    if announcement.start_date and announcement.start_date > announcement.expiration_date:
        raise HTTPException(
            status_code=400, detail="Start date cannot be after the expiration date")

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    document = {
        "title": announcement.title,
        "message": announcement.message,
        "start_date": announcement.start_date.isoformat() if announcement.start_date else None,
        "expiration_date": announcement.expiration_date.isoformat(),
        "created_by": teacher["username"],
        "created_by_display_name": teacher["display_name"],
        "created_at": now,
        "updated_at": now,
    }

    result = announcements_collection.insert_one(document)
    created_announcement = announcements_collection.find_one({"_id": result.inserted_id})

    return serialize_announcement(created_announcement)


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    announcement: AnnouncementUpdate,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement."""
    require_signed_in_user(teacher_username)

    try:
        object_id = ObjectId(announcement_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Announcement not found")

    existing_announcement = announcements_collection.find_one({"_id": object_id})
    if not existing_announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    updates = announcement.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400, detail="At least one field must be provided")

    next_start_date = updates.get(
        "start_date",
        parse_date(existing_announcement.get("start_date"))
    )
    next_expiration_date = updates.get(
        "expiration_date",
        parse_date(existing_announcement.get("expiration_date"))
    )

    if next_expiration_date and next_expiration_date < date.today():
        raise HTTPException(
            status_code=400, detail="Expiration date must be today or later")

    if next_start_date and next_expiration_date and next_start_date > next_expiration_date:
        raise HTTPException(
            status_code=400, detail="Start date cannot be after the expiration date")

    normalized_updates = {}
    for field_name, field_value in updates.items():
        if isinstance(field_value, date):
            normalized_updates[field_name] = field_value.isoformat()
        else:
            normalized_updates[field_name] = field_value

    normalized_updates["updated_at"] = datetime.utcnow().replace(
        microsecond=0).isoformat() + "Z"

    announcements_collection.update_one(
        {"_id": object_id},
        {"$set": normalized_updates}
    )

    updated_announcement = announcements_collection.find_one({"_id": object_id})
    return serialize_announcement(updated_announcement)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement."""
    require_signed_in_user(teacher_username)

    try:
        object_id = ObjectId(announcement_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Announcement not found")

    delete_result = announcements_collection.delete_one({"_id": object_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}