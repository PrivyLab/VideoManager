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
    use_tor: Optional[bool] = False             # Route through Tor SOCKS5 proxy (legacy alias)
    custom_proxy: Optional[str] = None          # Any custom proxy: http://, https://, socks5://
    routing_mode: Optional[str] = "direct"      # "direct", "warp", "tor"

    # Pre-download section trimming (optional)
    trim_start: Optional[str] = None            # e.g. "01:30" or "90"
    trim_end: Optional[str] = None              # e.g. "04:15" or "255"

class InspectRequest(BaseModel):
    url: str
    referer: Optional[str] = None
    use_tor: Optional[bool] = False
    custom_proxy: Optional[str] = None
    routing_mode: Optional[str] = "direct"
    cookies_from_browser: Optional[str] = None

class BatchDownloadItem(BaseModel):
    url: str
    custom_title: Optional[str] = None
    trim_start: Optional[str] = None
    trim_end: Optional[str] = None

class BatchDownloadRequest(BaseModel):
    items: Optional[List[BatchDownloadItem]] = None
    urls: Optional[List[str]] = None
    quality: Optional[str] = "best"
    downloader_type: Optional[str] = "auto"
    custom_chunks: Optional[int] = 4
    download_folder: Optional[str] = None
    cookies_from_browser: Optional[str] = None
    referer: Optional[str] = None
    routing_mode: Optional[str] = "direct"
    custom_proxy: Optional[str] = None
    use_tor: Optional[bool] = False

class PlaylistInspectRequest(BaseModel):
    url: str
    referer: Optional[str] = None
    use_tor: Optional[bool] = False
    custom_proxy: Optional[str] = None
    routing_mode: Optional[str] = "direct"
    cookies_from_browser: Optional[str] = None
    max_entries: Optional[int] = 100

class PlaylistItem(BaseModel):
    index: int
    id: str
    title: str
    url: str
    duration: Optional[float] = 0
    thumbnail: Optional[str] = ""
    uploader: Optional[str] = ""

class PlaylistInspectResponse(BaseModel):
    is_playlist: bool
    title: str
    id: Optional[str] = ""
    uploader: Optional[str] = ""
    description: Optional[str] = ""
    total_count: int
    items: List[PlaylistItem]

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

class ProxyEndpointStatus(BaseModel):
    available: bool
    proxy: str
    source: str
    is_active: bool
    exit_ip: Optional[str] = None
    message: str

class NetworkStatusResponse(BaseModel):
    in_docker: bool
    warp: ProxyEndpointStatus
    tor: ProxyEndpointStatus

class TrimRequest(BaseModel):
    start_time: float
    end_time: float
    title: Optional[str] = None
    mode: Optional[str] = "fast"  # "fast" or "reencode"
    extract_audio: Optional[bool] = False

class ExtractAudioRequest(BaseModel):
    format: Optional[str] = "mp3"  # "mp3", "m4a", "aac", "wav"
    bitrate: Optional[str] = "192k"
    title: Optional[str] = None

class CompressVideoRequest(BaseModel):
    preset: Optional[str] = "balanced"  # "light", "balanced", "discord"
    resolution: Optional[str] = "same"   # "same", "1080p", "720p", "480p"
    title: Optional[str] = None

class CreateGifRequest(BaseModel):
    start_time: Optional[float] = 0.0
    duration: Optional[float] = 5.0
    fps: Optional[int] = 15
    width: Optional[int] = 480
    title: Optional[str] = None
