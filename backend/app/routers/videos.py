import os
from pathlib import Path
from typing import Optional, Tuple
from fastapi import APIRouter, HTTPException, Header, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from app.database import db_get_all_videos, db_get_video, db_delete_video
from app.config import DEFAULT_VIDEOS_DIR, VIDEOS_DIR
from app.models import StitchRequest
from app.services.download_manager import download_manager
from app.services.video_stitcher import VideoStitcher

router = APIRouter(prefix="/api/videos", tags=["videos"])

def detect_content_type(file_path: Path) -> Tuple[str, str]:
    """
    Detect the real media container type by reading magic bytes from the file,
    not by trusting the file extension (which can be misleading after yt-dlp downloads).

    Returns (content_type, real_extension).
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
    except Exception:
        return "video/mp4", "mp4"

    # MPEG-TS: sync byte 0x47 at offset 0, 188, 376...
    if header[0:1] == b'\x47':
        return "video/mp2t", "ts"

    # MP4 / M4V / M4A — ftyp box at offset 4
    if header[4:8] in (b'ftyp', b'moov', b'mdat'):
        return "video/mp4", "mp4"

    # WebM / MKV — EBML header
    if header[0:4] == b'\x1a\x45\xdf\xa3':
        # Distinguish WebM from MKV by DocType (further into EBML, heuristic by ext)
        if file_path.suffix.lower() == ".webm":
            return "video/webm", "webm"
        return "video/x-matroska", "mkv"

    # AVI
    if header[0:4] == b'RIFF' and header[8:12] == b'AVI ':
        return "video/x-msvideo", "avi"

    # FLV
    if header[0:3] == b'FLV':
        return "video/x-flv", "flv"

    # OGG
    if header[0:4] == b'OggS':
        return "video/ogg", "ogg"

    # MP3
    if header[0:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2') or header[0:3] == b'ID3':
        return "audio/mpeg", "mp3"

    # M4A / AAC in MP4
    if file_path.suffix.lower() in (".m4a", ".aac"):
        return "audio/mp4", "m4a"

    # Fallback: trust extension
    ext = file_path.suffix.lower().lstrip(".")
    type_map = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "ts": "video/mp2t",
        "mov": "video/quicktime",
        "avi": "video/x-msvideo",
        "flv": "video/x-flv",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "ogg": "video/ogg",
    }
    return type_map.get(ext, "application/octet-stream"), ext


@router.get("")
async def list_videos(status_filter: Optional[str] = None):
    videos = db_get_all_videos(status_filter)
    return {"videos": videos}


@router.post("/stitch")
async def stitch_videos_endpoint(req: StitchRequest):
    """Stitches multiple completed video clips into a single continuous video."""
    if not req.video_ids or len(req.video_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 videos are required for stitching")
    try:
        job_id = await download_manager.start_stitch(
            video_ids=req.video_ids,
            title=req.title,
            mode=req.mode or "auto"
        )
        return {"success": True, "video_id": job_id}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stitch/preview")
async def preview_stitch_endpoint(req: StitchRequest):
    """Returns analysis and total duration/size for selected clips before stitching."""
    if not req.video_ids or len(req.video_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 videos are required")

    clips = []
    total_duration = 0.0
    total_size = 0
    resolutions = set()

    stitcher = VideoStitcher("preview")
    for vid in req.video_ids:
        video = db_get_video(vid)
        if not video or not video.get("file_path"):
            continue
        p = Path(video["file_path"])
        if not p.exists():
            continue
        info = stitcher.probe_video(p)
        clips.append({
            "id": vid,
            "title": video.get("title") or p.name,
            "duration": info["duration"] or video.get("duration", 0),
            "size": info["size"],
            "resolution": info["resolution"],
            "video_codec": info["video_codec"],
            "has_audio": info["has_audio"],
            "thumbnail_url": video.get("thumbnail_url") or f"/api/videos/{vid}/thumbnail",
        })
        total_duration += (info["duration"] or video.get("duration", 0))
        total_size += info["size"]
        if info["resolution"] != "unknown":
            resolutions.add(info["resolution"])

    return {
        "clips": clips,
        "total_clips": len(clips),
        "total_duration": total_duration,
        "total_size": total_size,
        "compatible_for_fast": len(resolutions) <= 1,
    }


@router.get("/{video_id}")
async def get_video(video_id: str):
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"video": video}


@router.get("/{video_id}/info")
async def get_video_file_info(video_id: str):
    """Returns detected content type and real file info from magic bytes."""
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")
    file_path = Path(video["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    content_type, real_ext = detect_content_type(file_path)
    file_size = file_path.stat().st_size
    return {
        "file_path": str(file_path),
        "stated_format": video.get("file_format"),
        "detected_content_type": content_type,
        "detected_extension": real_ext,
        "file_size": file_size,
        "streamable_in_browser": content_type in ("video/mp4", "video/webm", "video/ogg"),
        "needs_remux": real_ext == "ts" or content_type == "video/mp2t",
    }


@router.delete("/{video_id}")
async def delete_video(video_id: str):
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = video.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db_delete_video(video_id)
    return {"success": True}


@router.get("/{video_id}/download")
async def download_file(video_id: str):
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video file not found")

    file_path = Path(video["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File on disk not found")

    content_type, real_ext = detect_content_type(file_path)
    safe_title = (video.get("title") or "video").replace("/", "_").replace("\\", "_")
    filename = f"{safe_title}.{real_ext}"
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@router.get("/{video_id}/thumbnail")
async def get_video_thumbnail(video_id: str):
    """Serves the video's thumbnail image or generates one on-the-fly with ffmpeg."""
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # If it has an external HTTP thumbnail URL, redirect to it
    thumb_url = video.get("thumbnail_url")
    if thumb_url and thumb_url.startswith(("http://", "https://")):
        return Response(status_code=307, headers={"Location": thumb_url})

    file_path = video.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="No video file associated")

    video_p = Path(file_path)
    if not video_p.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    thumb_p = video_p.parent / f"{video_p.stem}_thumb.jpg"
    if not thumb_p.exists():
        stitcher = VideoStitcher(video_id)
        generated = await stitcher.generate_thumbnail(video_p, thumb_p)
        if not generated or not thumb_p.exists():
            raise HTTPException(status_code=404, detail="Could not generate thumbnail")

    return FileResponse(thumb_p, media_type="image/jpeg")


@router.get("/{video_id}/stream")
async def stream_video(video_id: str, range: Optional[str] = Header(None)):
    """
    Stream video with HTTP Range support.
    Detects the real container format from magic bytes so the browser
    gets the correct Content-Type regardless of the file extension.
    """
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = Path(video["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    file_size = file_path.stat().st_size
    content_type, real_ext = detect_content_type(file_path)

    # MPEG-TS (.ts) is not natively playable in browser <video> tags.
    # Return a clear error with a hint instead of silently serving unplayable bytes.
    if content_type == "video/mp2t":
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unplayable_format",
                "message": (
                    "This file is a raw MPEG-TS transport stream (.ts). "
                    "Browsers cannot play .ts files natively. "
                    "Install ffmpeg and re-download the video so yt-dlp can remux it to .mp4."
                ),
                "fix": "brew install ffmpeg  (then re-download)",
                "file": str(file_path),
            }
        )

    if range:
        range_str = range.replace("bytes=", "")
        parts = range_str.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        end = min(end, file_size - 1)
        chunk_size = (end - start) + 1

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    data = f.read(min(bytes_left, 65536))
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(
            iterfile(),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers
        )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": content_type,
    }
    return FileResponse(file_path, headers=headers, media_type=content_type)
