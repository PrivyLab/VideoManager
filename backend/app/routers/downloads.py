from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from app.models import (
    DownloadRequest,
    InspectRequest,
    BatchDownloadRequest,
    BatchDownloadItem,
    PlaylistInspectRequest,
    PlaylistInspectResponse
)
from app.services.download_manager import download_manager
from app.services.ytdlp_downloader import YtDlpDownloader
from app.services.chunk_engine import ChunkEngine
from app.services.stream_auth import is_client_localhost
from app.database import db_get_video, db_get_all_videos

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

@router.post("")
async def create_download(req: DownloadRequest, request: Request):
    if not is_client_localhost(request):
        raise HTTPException(status_code=403, detail="Access denied: Downloads can only be initiated from localhost.")
    if not req.url:
        raise HTTPException(status_code=400, detail="Video URL is required")
    video_id = await download_manager.start_download(req)
    return {"success": True, "video_id": video_id}

@router.post("/batch")
async def create_batch_downloads(req: BatchDownloadRequest, request: Request):
    """Queues a batch of video URLs for sequential / concurrent downloading."""
    if not is_client_localhost(request):
        raise HTTPException(status_code=403, detail="Access denied: Downloads can only be initiated from localhost.")
    items_to_download = []
    if req.items and len(req.items) > 0:
        items_to_download = req.items
    elif req.urls and len(req.urls) > 0:
        for u in req.urls:
            u_clean = u.strip()
            if u_clean:
                items_to_download.append(BatchDownloadItem(url=u_clean))

    if not items_to_download:
        raise HTTPException(status_code=400, detail="At least one valid URL is required for batch download.")

    video_ids = []
    for item in items_to_download:
        dl_req = DownloadRequest(
            url=item.url,
            quality=req.quality or "best",
            downloader_type=req.downloader_type or "auto",
            custom_chunks=req.custom_chunks or 4,
            custom_title=item.custom_title,
            download_folder=req.download_folder,
            cookies_from_browser=req.cookies_from_browser,
            referer=req.referer,
            use_tor=req.use_tor or False,
            custom_proxy=req.custom_proxy,
            routing_mode=req.routing_mode or "direct",
            trim_start=item.trim_start,
            trim_end=item.trim_end
        )
        vid_id = await download_manager.start_download(dl_req)
        video_ids.append(vid_id)

    return {
        "success": True,
        "count": len(video_ids),
        "video_ids": video_ids
    }

@router.post("/playlist/inspect")
async def inspect_playlist(req: PlaylistInspectRequest):
    """Inspects a playlist or channel to list all episodes/videos with checkboxes without downloading."""
    url = req.url.strip() if req.url else ""
    if not url:
        raise HTTPException(status_code=400, detail="Playlist URL is required.")

    try:
        data = YtDlpDownloader.extract_playlist(
            url=url,
            referer=req.referer,
            use_tor=req.use_tor or False,
            custom_proxy=req.custom_proxy,
            routing_mode=req.routing_mode,
            cookies_from_browser=req.cookies_from_browser,
            max_entries=req.max_entries or 100
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playlist extraction failed: {str(e)}")

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

