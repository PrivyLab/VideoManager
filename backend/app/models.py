from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = "best"         # "best", "1080p", "720p", "480p", "audio"
    downloader_type: Optional[str] = "auto" # "auto", "ytdlp", "chunked"
    custom_chunks: Optional[int] = 4
    chunk_urls: Optional[List[str]] = None
    custom_title: Optional[str] = None
    download_folder: Optional[str] = None

    # Anti-blocking options
    cookies_from_browser: Optional[str] = None  # "chrome", "firefox", "safari", "edge"
    referer: Optional[str] = None               # Source page URL where video was embedded
    use_tor: Optional[bool] = False             # Route through Tor SOCKS5 proxy
    custom_proxy: Optional[str] = None          # Any custom proxy: http://, https://, socks5://

class InspectRequest(BaseModel):
    url: str
    referer: Optional[str] = None
    use_tor: Optional[bool] = False
    custom_proxy: Optional[str] = None

class VideoResponse(BaseModel):
    id: str
    url: str
    title: Optional[str] = None
    duration: Optional[float] = 0
    file_path: Optional[str] = None
    file_size: Optional[int] = 0
    file_format: Optional[str] = None
    thumbnail_url: Optional[str] = None
    resolution: Optional[str] = None
    status: str
    progress: float = 0.0
    speed: Optional[str] = ""
    eta: Optional[str] = ""
    error_message: Optional[str] = None
    downloader_type: Optional[str] = "ytdlp"
    chunks_total: Optional[int] = 0
    chunks_completed: Optional[int] = 0
    created_at: str
    completed_at: Optional[str] = None

class ProgressUpdate(BaseModel):
    video_id: str
    status: str
    progress: float
    speed: str = ""
    eta: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    chunks_total: int = 0
    chunks_completed: int = 0
    message: str = ""

class SystemSettings(BaseModel):
    download_folder: str

class FolderBrowseItem(BaseModel):
    name: str
    path: str
    is_dir: bool

class FolderBrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    folders: List[FolderBrowseItem]

class StitchRequest(BaseModel):
    video_ids: List[str]
    title: Optional[str] = None
    mode: Optional[str] = "auto"  # "auto", "fast", "reencode"
