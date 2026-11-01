import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

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
        status TEXT NOT NULL, -- 'queued', 'downloading', 'merging', 'completed', 'failed', 'cancelled'
        progress REAL DEFAULT 0,
        speed TEXT DEFAULT '',
        eta TEXT DEFAULT '',
        error_message TEXT,
        downloader_type TEXT DEFAULT 'ytdlp', -- 'ytdlp', 'chunked', 'direct'
        chunks_total INTEGER DEFAULT 0,
        chunks_completed INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        completed_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def db_create_video(video_data: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    keys = list(video_data.keys())
    placeholders = ",".join(["?" for _ in keys])
    col_names = ",".join(keys)
    values = [video_data[k] for k in keys]
    cursor.execute(f"INSERT INTO videos ({col_names}) VALUES ({placeholders})", values)
    conn.commit()
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
    conn.commit()
    conn.close()

