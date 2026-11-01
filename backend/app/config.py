import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
STORAGE_DIR = BASE_DIR / "storage"

def find_env_file() -> Optional[Path]:
    """Finds .env file at workspace root, backend dir, or current working dir."""
    candidates = [
        ROOT_DIR / ".env",
        BASE_DIR / ".env",
        Path.cwd() / ".env",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None

def get_env_download_dir() -> Optional[Path]:
    """
    Checks if a .env file is present and extracts the download video directory from it.
    Checks common variable names: DOWNLOAD_DIR, DOWNLOAD_FOLDER, DOWNLOADS_DIR,
    VIDEOS_DIR, VIDEO_DOWNLOAD_DIR, DOWNLOAD_VIDEOS_DIR, DOWNLOAD_PATH, etc.
    """
    env_file = find_env_file()
    if not env_file:
        return None

    env_dict = {}
    try:
        from dotenv import dotenv_values
        env_dict = dotenv_values(env_file)
    except Exception:
        pass

    # Fallback to direct parsing if dotenv_values returned empty
    if not env_dict:
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_dict[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass

    possible_keys = [
        "DOWNLOAD_DIR", "DOWNLOAD_FOLDER", "DOWNLOADS_DIR",
        "VIDEOS_DIR", "VIDEO_DOWNLOAD_DIR", "DOWNLOAD_VIDEOS_DIR",
        "DOWNLOAD_PATH", "VIDEOS_PATH", "DOWNLOAD_VIDEO_DIR"
    ]

    for key in possible_keys:
        val = env_dict.get(key)
        if val is None:
            val = os.environ.get(key)
        if val and str(val).strip():
            clean_str = str(val).strip().strip('"').strip("'")
            if clean_str:
                p = Path(clean_str).expanduser().resolve()
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                return p

    # If .env is present, check any key matching DOWNLOAD and DIR/FOLDER/PATH
    for k, v in env_dict.items():
        if "DOWNLOAD" in k.upper() and ("DIR" in k.upper() or "PATH" in k.upper() or "FOLDER" in k.upper()):
            clean_str = str(v).strip().strip('"').strip("'")
            if clean_str:
                p = Path(clean_str).expanduser().resolve()
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                return p

    # Fallback to os.environ if set
    env_os = os.environ.get("DOWNLOAD_DIR")
    if env_os and env_os.strip():
        p = Path(env_os.strip()).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    return None

# Load .env into os.environ if present at startup
_env_path = find_env_file()
if _env_path:
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path, override=True)
    except Exception:
        pass

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
WARP_PROXY_ENV = os.environ.get("WARP_PROXY")
RUNNING_IN_DOCKER = (
    os.environ.get("RUNNING_IN_DOCKER", "false").lower() in ("true", "1", "yes")
    or Path("/.dockerenv").exists()
)

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

def get_active_warp_proxy() -> Optional[str]:
    """
    Auto-detect Cloudflare WARP SOCKS5 proxy:
    1. WARP_PROXY environment variable (e.g. docker-compose socks5://warp:1080)
    2. warp:1080 (Docker network)
    3. 127.0.0.1:1080 (Host mapped container or local warp client)
    """
    import socket
    if WARP_PROXY_ENV and WARP_PROXY_ENV.strip():
        return WARP_PROXY_ENV.strip()

    candidates = [
        ("warp", 1080),       # Docker Compose service
        ("127.0.0.1", 1080),  # Local port mapping
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
    """
    Get the currently configured default download directory.
    Priority:
    1. If .env file is present, take download video directory from .env instead of settings.json.
    2. Otherwise, take download video directory from settings.json.
    3. Fallback to DEFAULT_VIDEOS_DIR.
    """
    env_dir = get_env_download_dir()
    if env_dir:
        return env_dir

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
    """
    Save user-chosen default download directory.
    If .env is present, updates .env; also writes to settings.json for backward compatibility.
    """
    import json
    p = Path(path_str).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)

    env_file = find_env_file()
    if env_file:
        try:
            from dotenv import set_key
            set_key(env_file, "DOWNLOAD_DIR", str(p))
            os.environ["DOWNLOAD_DIR"] = str(p)
        except Exception:
            pass

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

    # If keep_final is False and a specific final file_path is given, delete it directly
    if not keep_final and file_path:
        try:
            p = Path(file_path)
            if p.exists() and p.is_file():
                p.unlink()
        except Exception:
            pass

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
