import sqlite3
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _run_migrations(cursor):
    """Apply any missing schema migrations safely."""
    cursor.execute("PRAGMA table_info(videos)")
    cols = {row["name"] for row in cursor.fetchall()}
    if "content_hash" not in cols:
        cursor.execute("ALTER TABLE videos ADD COLUMN content_hash TEXT")
    if "session_id" not in cols:
        cursor.execute("ALTER TABLE videos ADD COLUMN session_id TEXT")

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        duration REAL DEFAULT 0,
        file_path TEXT,
        file_size INTEGER DEFAULT 0,
        file_format TEXT,
        thumbnail_url TEXT,
        resolution TEXT,
        status TEXT NOT NULL,
        progress REAL DEFAULT 0,
        speed TEXT DEFAULT '',
        eta TEXT DEFAULT '',
        error_message TEXT,
        downloader_type TEXT DEFAULT 'ytdlp',
        chunks_total INTEGER DEFAULT 0,
        chunks_completed INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        content_hash TEXT,
        session_id TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stream_security (
        video_id TEXT PRIMARY KEY,
        pin TEXT NOT NULL,
        pin_enabled INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        color TEXT DEFAULT '#6366f1',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    # Run migrations for existing DBs
    _run_migrations(cursor)
    conn.commit()
    conn.close()

def compute_url_hash(url: str) -> str:
    """Compute a stable SHA-256 hash of the normalized URL."""
    normalized = url.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()

def db_find_duplicate(url: str) -> Optional[Dict[str, Any]]:
    """Return first completed video with the same URL hash, or None."""
    h = compute_url_hash(url)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM videos WHERE content_hash = ? AND status = 'completed' LIMIT 1",
        (h,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def db_create_video(video_data: Dict[str, Any]):
    if "created_at" not in video_data:
        from datetime import datetime
        video_data["created_at"] = datetime.now().isoformat()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        keys = list(video_data.keys())
        placeholders = ",".join(["?" for _ in keys])
        col_names = ",".join(keys)
        values = [video_data[k] for k in keys]
        cursor.execute(f"INSERT INTO videos ({col_names}) VALUES ({placeholders})", values)
        conn.commit()
    finally:
        conn.close()

def db_update_video(video_id: str, updates: Dict[str, Any]):
    if not updates:
        return
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [video_id]
    cursor.execute(f"UPDATE videos SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def db_get_video(video_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def db_get_all_videos(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM videos WHERE status = ? ORDER BY created_at DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM videos ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_delete_video(video_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    cursor.execute("DELETE FROM stream_security WHERE video_id = ?", (video_id,))
    conn.commit()
    conn.close()

def db_get_stream_security(video_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stream_security WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def db_set_stream_security(video_id: str, pin: str, pin_enabled: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO stream_security (video_id, pin, pin_enabled, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            pin = excluded.pin,
            pin_enabled = excluded.pin_enabled
    """, (video_id, pin, 1 if pin_enabled else 0, now))
    conn.commit()
    conn.close()

# ── Session CRUD ──────────────────────────────────────────────────────────────

def db_get_all_sessions() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def db_create_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, name, description, color, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_data["id"], session_data["name"], session_data.get("description", ""),
         session_data.get("color", "#6366f1"), session_data["created_at"], session_data["updated_at"])
    )
    conn.commit()
    conn.close()
    return session_data

def db_update_session(session_id: str, updates: Dict[str, Any]):
    if not updates:
        return
    conn = get_connection()
    cursor = conn.cursor()
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [session_id]
    cursor.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def db_delete_session(session_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    # Unassign videos from this session
    cursor.execute("UPDATE videos SET session_id = NULL WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def db_assign_video_session(video_id: str, session_id: Optional[str]):
    db_update_video(video_id, {"session_id": session_id})
