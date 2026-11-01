import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DEFAULT_VIDEOS_DIR = Path(os.environ.get("DOWNLOAD_DIR", str(STORAGE_DIR / "videos"))).expanduser().resolve()
VIDEOS_DIR = DEFAULT_VIDEOS_DIR  # Alias for backwards compatibility
THUMBNAILS_DIR = STORAGE_DIR / "thumbnails"
CHUNKS_DIR = STORAGE_DIR / "temp_chunks"
DB_PATH = STORAGE_DIR / "videomanager.db"

# Ensure all default storage directories exist
for folder in [STORAGE_DIR, DEFAULT_VIDEOS_DIR, THUMBNAILS_DIR, CHUNKS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Settings file to persist default download directory configured by user
SETTINGS_FILE = STORAGE_DIR / "settings.json"

TOR_PROXY_ENV = os.environ.get("TOR_PROXY")

def get_active_tor_proxy() -> Optional[str]:
    """
    Auto-detect active Tor SOCKS5 proxy:
    1. TOR_PROXY environment variable (e.g. docker-compose socks5://tor:9050)
    2. Port 9150 (Tor Browser Mac App - default)
    3. Port 9050 (Tor daemon or local container)
    4. tor:9050 (Docker network)
    """
    import socket
    if TOR_PROXY_ENV and TOR_PROXY_ENV.strip():
        return TOR_PROXY_ENV.strip()

    candidates = [
        ("127.0.0.1", 9150),  # Tor Browser Mac App
        ("127.0.0.1", 9050),  # Tor daemon / local Docker container
        ("tor", 9050),        # Docker Compose service
    ]
    for host, port in candidates:
        try:
            s = socket.create_connection((host, port), timeout=0.5)
            s.close()
            return f"socks5://{host}:{port}"
        except Exception:
            pass
    return None

def get_configured_download_dir() -> Path:
    """Get the currently configured default download directory."""
    if SETTINGS_FILE.exists():
        try:
            import json
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                custom_path = data.get("download_folder")
                if custom_path:
                    p = Path(custom_path).expanduser().resolve()
                    p.mkdir(parents=True, exist_ok=True)
                    return p
        except Exception:
            pass
    return DEFAULT_VIDEOS_DIR

def set_configured_download_dir(path_str: str) -> Path:
    """Save user-chosen default download directory."""
    import json
    p = Path(path_str).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"download_folder": str(p)}, f)
    return p

def cleanup_orphaned_temp_files():
    """Removes leftover .part, .ytdl, and -Frag* files from storage."""
    import shutil
    storage_dirs = [DEFAULT_VIDEOS_DIR, get_configured_download_dir()]
    for sdir in set(storage_dirs):
        if not sdir.exists():
            continue
        for p in sdir.glob("*"):
            if p.is_file() and (p.name.endswith((".part", ".ytdl")) or "-Frag" in p.name):
                try:
                    p.unlink()
                except Exception:
                    pass
    if CHUNKS_DIR.exists():
        for d in CHUNKS_DIR.glob("*"):
            if d.is_dir():
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass

def cleanup_video_artifacts(video_id: str, file_path: Optional[str] = None, keep_final: bool = False):
    """
    Clean up temporary fragments, .part, .ytdl, and chunks for a video ID.
    If keep_final is False, also deletes the final video file and thumbnail.
    """
    import shutil
    storage_dirs = [DEFAULT_VIDEOS_DIR, get_configured_download_dir()]
    if file_path:
        storage_dirs.append(Path(file_path).parent)

    for sdir in set(storage_dirs):
        if not sdir.exists():
            continue
        for f in sdir.glob(f"*{video_id}*"):
            try:
                if keep_final:
                    # Only delete temporary files (.part, .ytdl, fragments)
                    if f.name.endswith((".part", ".ytdl")) or "-Frag" in f.name:
                        f.unlink()
                else:
                    if f.is_file():
                        f.unlink()
                    elif f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
            except Exception:
                pass

    chunk_dir = CHUNKS_DIR / video_id
    if chunk_dir.exists():
        try:
            shutil.rmtree(chunk_dir, ignore_errors=True)
        except Exception:
            pass
