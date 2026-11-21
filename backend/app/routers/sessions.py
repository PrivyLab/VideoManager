import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.database import (
    db_get_all_sessions, db_get_session, db_create_session,
    db_update_session, db_delete_session, db_assign_video_session,
    db_get_all_videos, db_find_duplicate, compute_url_hash
)
from app.models import SessionCreateRequest, SessionUpdateRequest, AssignSessionRequest, DuplicateCheckResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("")
async def list_sessions():
    """List all sessions with their video counts."""
    sessions = db_get_all_sessions()
    all_videos = db_get_all_videos()
    # Count videos per session
    counts: dict = {}
    for v in all_videos:
        sid = v.get("session_id")
        if sid:
            counts[sid] = counts.get(sid, 0) + 1
    result = []
    for s in sessions:
        s["video_count"] = counts.get(s["id"], 0)
        result.append(s)
    return {"sessions": result}

@router.post("")
async def create_session(req: SessionCreateRequest):
    """Create a new session."""
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Session name is required")
    now = datetime.utcnow().isoformat()
    session_id = str(uuid.uuid4())[:12]
    data = {
        "id": session_id,
        "name": req.name.strip(),
        "description": req.description or "",
        "color": req.color or "#6366f1",
        "created_at": now,
        "updated_at": now,
    }
    session = db_create_session(data)
    return {"success": True, "session": session}

@router.get("/{session_id}")
async def get_session(session_id: str):
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session}

@router.patch("/{session_id}")
async def update_session(session_id: str, req: SessionUpdateRequest):
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    updates = {}
    if req.name is not None:
        if not req.name.strip():
            raise HTTPException(status_code=400, detail="Session name cannot be empty")
        updates["name"] = req.name.strip()
    if req.description is not None:
        updates["description"] = req.description
    if req.color is not None:
        updates["color"] = req.color
    if updates:
        db_update_session(session_id, updates)
    updated = db_get_session(session_id)
    return {"success": True, "session": updated}

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db_delete_session(session_id)
    return {"success": True}

@router.post("/{session_id}/assign/{video_id}")
async def assign_video_to_session(session_id: str, video_id: str):
    """Assign a video to a session."""
    session = db_get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db_assign_video_session(video_id, session_id)
    return {"success": True}

@router.delete("/{session_id}/assign/{video_id}")
async def unassign_video_from_session(session_id: str, video_id: str):
    """Remove a video from a session (unassign)."""
    db_assign_video_session(video_id, None)
    return {"success": True}

@router.post("/check-duplicate")
async def check_duplicate(payload: dict):
    """Check if a URL has already been downloaded."""
    url = payload.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    existing = db_find_duplicate(url)
    if existing:
        return DuplicateCheckResponse(
            is_duplicate=True,
            existing_video=existing,
            message=f"This URL was already downloaded as '{existing.get('title', 'Unknown')}'"
        )
    return DuplicateCheckResponse(is_duplicate=False, existing_video=None, message="No duplicate found")
