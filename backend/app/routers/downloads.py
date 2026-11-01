from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models import DownloadRequest, InspectRequest
from app.services.download_manager import download_manager
from app.services.ytdlp_downloader import YtDlpDownloader
from app.services.chunk_engine import ChunkEngine
from app.database import db_get_video, db_get_all_videos

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

@router.post("")
async def create_download(req: DownloadRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="Video URL is required")
    video_id = await download_manager.start_download(req)
    return {"success": True, "video_id": video_id}

@router.post("/inspect")
async def inspect_url(req: InspectRequest):
    """Inspects a URL to get title, duration, thumbnail, formats, or chunk capability."""
    url = req.url
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Try yt-dlp first
    try:
        info = YtDlpDownloader.extract_info(url)
        return {"source": "ytdlp", "info": info}
    except Exception as ytdlp_err:
        # If yt-dlp fails (e.g. direct raw mp4 or unknown stream), probe chunk engine
        engine = ChunkEngine("probe")
        probe = await engine.probe_url(url)
        return {
            "source": "direct",
            "info": {
                "title": url.split("/")[-1].split("?")[0] or "Direct Stream",
                "duration": 0,
                "thumbnail": "",
                "formats": [],
                "probe": probe
            },
            "ytdlp_error": str(ytdlp_err)
        }

@router.get("/active")
async def get_active_downloads():
    all_videos = db_get_all_videos()
    active = [v for v in all_videos if v["status"] in ("queued", "downloading", "merging")]
    return {"active": active}

@router.post("/{video_id}/cancel")
async def cancel_download(video_id: str):
    res = await download_manager.cancel_download(video_id)
    return {"success": res}

@router.post("/{video_id}/retry")
async def retry_download(video_id: str):
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    req = DownloadRequest(
        url=video["url"],
        downloader_type=video.get("downloader_type") or "auto",
        custom_title=video.get("title")
    )
    new_id = await download_manager.start_download(req)
    return {"success": True, "new_video_id": new_id}

