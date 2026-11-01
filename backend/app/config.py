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
