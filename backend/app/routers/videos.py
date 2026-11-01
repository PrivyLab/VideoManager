import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from fastapi import APIRouter, HTTPException, Header, Response, Request, status
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from app.database import db_get_all_videos, db_get_video, db_delete_video, db_create_video
from app.config import DEFAULT_VIDEOS_DIR, VIDEOS_DIR, cleanup_video_artifacts
from app.models import (
    StitchRequest, ExtractAudioRequest, CompressVideoRequest, CreateGifRequest, TrimRequest,
    PinVerifyRequest, PinConfigRequest
)
from app.services.download_manager import download_manager
from app.services.video_stitcher import VideoStitcher
from app.services.media_tools import extract_audio, compress_video, create_gif, trim_video
from app.services.qr_generator import get_local_wifi_ip, generate_qr_svg
from app.services.faststart import ensure_faststart
from app.services.stream_auth import (
    generate_stream_token, verify_stream_token, get_or_create_pin,
    set_pin_config, verify_video_pin, is_client_localhost, is_stream_authorized
)

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
async def list_videos(request: Request, status_filter: Optional[str] = None):
    # Shield video library: only allow local desktop client to list the library
    if not is_client_localhost(request):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Full video library can only be accessed locally on this machine."
        )
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

    cleanup_video_artifacts(video_id, video.get("file_path"))
    db_delete_video(video_id)
    return {"success": True}


@router.get("/{video_id}/download")
async def download_file(video_id: str, request: Request):
    if not is_stream_authorized(request, video_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Valid cryptographic stream token or PIN authentication required on local Wi-Fi."
        )

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


@router.post("/{video_id}/extract-audio")
async def extract_audio_endpoint(video_id: str, req: ExtractAudioRequest):
    """Extracts MP3, M4A, or AAC audio from a downloaded video."""
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")

    src_path = Path(video["file_path"])
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source video file not found on disk")

    fmt = (req.format or "mp3").lower().strip()
    bitrate = req.bitrate or "192k"
    new_id = str(uuid.uuid4())[:8]

    safe_title = req.title.strip() if req.title and req.title.strip() else f"{video.get('title', 'audio')}_audio"
    out_filename = f"{new_id}_{safe_title.replace(' ', '_').replace('/', '_')}.{fmt}"
    out_path = src_path.parent / out_filename

    try:
        res = await extract_audio(src_path, out_path, audio_format=fmt, bitrate=bitrate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {str(e)}")

    now = datetime.utcnow().isoformat()
    record = {
        "id": new_id,
        "url": f"extracted://{video_id}",
        "title": safe_title,
        "duration": res["duration"] or video.get("duration", 0),
        "file_path": str(out_path),
        "file_size": res["file_size"],
        "file_format": fmt,
        "thumbnail_url": video.get("thumbnail_url") or "",
        "resolution": "Audio",
        "status": "completed",
        "progress": 100.0,
        "speed": "",
        "eta": "",
        "error_message": "",
        "downloader_type": "audio",
        "chunks_total": 0,
        "chunks_completed": 0,
        "created_at": now,
        "completed_at": now
    }
    db_create_video(record)
    await download_manager.broadcast({"event": "video_created", "video": record})
    return {"success": True, "video": record}


@router.post("/{video_id}/compress")
async def compress_video_endpoint(video_id: str, req: CompressVideoRequest):
    """Compresses large video using H.264 CRF for WhatsApp, Discord, or web sharing."""
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")

    src_path = Path(video["file_path"])
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source video file not found on disk")

    new_id = str(uuid.uuid4())[:8]
    safe_title = req.title.strip() if req.title and req.title.strip() else f"{video.get('title', 'video')}_compressed"
    out_filename = f"{new_id}_{safe_title.replace(' ', '_').replace('/', '_')}.mp4"
    out_path = src_path.parent / out_filename

    try:
        res = await compress_video(src_path, out_path, preset=req.preset or "balanced", resolution=req.resolution or "same")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video compression failed: {str(e)}")

    now = datetime.utcnow().isoformat()
    record = {
        "id": new_id,
        "url": f"compressed://{video_id}",
        "title": safe_title,
        "duration": res["duration"] or video.get("duration", 0),
        "file_path": str(out_path),
        "file_size": res["file_size"],
        "file_format": "mp4",
        "thumbnail_url": res.get("thumbnail_url") or video.get("thumbnail_url") or "",
        "resolution": res.get("resolution") or video.get("resolution") or "1080p",
        "status": "completed",
        "progress": 100.0,
        "speed": "",
        "eta": "",
        "error_message": "",
        "downloader_type": "compress",
        "chunks_total": 0,
        "chunks_completed": 0,
        "created_at": now,
        "completed_at": now
    }
    db_create_video(record)
    await download_manager.broadcast({"event": "video_created", "video": record})
    return {"success": True, "video": record}


@router.post("/{video_id}/gif")
async def create_gif_endpoint(video_id: str, req: CreateGifRequest):
    """Converts a video segment into a high-quality animated GIF with 2-pass palettegen."""
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")

    src_path = Path(video["file_path"])
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source video file not found on disk")

    new_id = str(uuid.uuid4())[:8]
    safe_title = req.title.strip() if req.title and req.title.strip() else f"{video.get('title', 'clip')}_gif"
    out_filename = f"{new_id}_{safe_title.replace(' ', '_').replace('/', '_')}.gif"
    out_path = src_path.parent / out_filename

    try:
        res = await create_gif(
            src_path,
            out_path,
            start_time=req.start_time or 0.0,
            duration=req.duration or 5.0,
            fps=req.fps or 15,
            width=req.width or 480
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GIF creation failed: {str(e)}")

    now = datetime.utcnow().isoformat()
    record = {
        "id": new_id,
        "url": f"gif://{video_id}",
        "title": safe_title,
        "duration": res["duration"],
        "file_path": str(out_path),
        "file_size": res["file_size"],
        "file_format": "gif",
        "thumbnail_url": video.get("thumbnail_url") or "",
        "resolution": res.get("resolution") or "480px",
        "status": "completed",
        "progress": 100.0,
        "speed": "",
        "eta": "",
        "error_message": "",
        "downloader_type": "gif",
        "chunks_total": 0,
        "chunks_completed": 0,
        "created_at": now,
        "completed_at": now
    }
    db_create_video(record)
    await download_manager.broadcast({"event": "video_created", "video": record})
    return {"success": True, "video": record}


@router.post("/{video_id}/trim")
async def trim_video_endpoint(video_id: str, req: TrimRequest):
    """Trims video between start and end timestamps, with optional audio extraction."""
    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")

    src_path = Path(video["file_path"])
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source video file not found on disk")

    new_id = str(uuid.uuid4())[:8]
    ext = "mp3" if req.extract_audio else "mp4"
    safe_title = req.title.strip() if req.title and req.title.strip() else f"{video.get('title', 'video')}_trimmed"
    out_filename = f"{new_id}_{safe_title.replace(' ', '_').replace('/', '_')}.{ext}"
    out_path = src_path.parent / out_filename

    try:
        res = await trim_video(
            src_path,
            out_path,
            start_time=req.start_time,
            end_time=req.end_time,
            mode=req.mode or "fast",
            extract_audio=bool(req.extract_audio)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trimming failed: {str(e)}")

    now = datetime.utcnow().isoformat()
    record = {
        "id": new_id,
        "url": f"trimmed://{video_id}",
        "title": safe_title,
        "duration": res["duration"],
        "file_path": str(out_path),
        "file_size": res["file_size"],
        "file_format": res.get("file_format", ext),
        "thumbnail_url": res.get("thumbnail_url") or video.get("thumbnail_url") or "",
        "resolution": res.get("resolution") or video.get("resolution") or "1080p",
        "status": "completed",
        "progress": 100.0,
        "speed": "",
        "eta": "",
        "error_message": "",
        "downloader_type": "audio" if req.extract_audio else "trim",
        "chunks_total": 0,
        "chunks_completed": 0,
        "created_at": now,
        "completed_at": now
    }
    db_create_video(record)
    await download_manager.broadcast({"event": "video_created", "video": record})
    return {"success": True, "video": record}


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


@router.api_route("/{video_id}/stream", methods=["GET", "HEAD"])
async def stream_video(video_id: str, request: Request):
    """
    Stream video with full RFC 7233 / 9110 HTTP Range support for mobile seeking.
    Ensures MP4 moov metadata atom is placed at the beginning of the file (FastStart)
    so mobile browsers (iOS Safari, Android Chrome) can seek forward instantly without
    stalling or buffering the entire video.
    Protected by HMAC-SHA256 tokens and PIN verification against Wi-Fi eavesdroppers.
    """
    if not is_stream_authorized(request, video_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Valid cryptographic stream token or PIN authentication required on local Wi-Fi."
        )

    video = db_get_video(video_id)
    if not video or not video.get("file_path"):
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = Path(video["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

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

    # Ensure MP4 faststart atom is at the beginning for instant mobile seeking
    if content_type == "video/mp4" or file_path.suffix.lower() in [".mp4", ".m4v", ".mov"]:
        await ensure_faststart(file_path)

    # Starlette FileResponse natively and asynchronously handles:
    # 1. 'Range: bytes=start-end' (sub-ranges)
    # 2. 'Range: bytes=start-' (open-ended seeks)
    # 3. 'Range: bytes=-N' (suffix range for footer/moov reading)
    # 4. HEAD requests (for duration and dimension probing)
    # 5. ETag and Last-Modified caching headers required by mobile Safari
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    }
    return FileResponse(file_path, headers=headers, media_type=content_type)


@router.get("/{video_id}/share-link")
async def get_video_share_link(video_id: str, port: Optional[int] = 8000):
    """Returns local Wi-Fi streaming URL with compact QR code and PIN security."""
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    local_ip = get_local_wifi_ip()
    token = generate_stream_token(video_id)
    pin, pin_enabled = get_or_create_pin(video_id)

    if pin_enabled and pin:
        watch_url = f"http://{local_ip}:{port}/watch/{video_id}?p={pin}"
        qr_endpoint = f"/api/videos/{video_id}/qr.svg?ip={local_ip}&port={port}&p={pin}"
    else:
        watch_url = f"http://{local_ip}:{port}/watch/{video_id}"
        qr_endpoint = f"/api/videos/{video_id}/qr.svg?ip={local_ip}&port={port}"
    stream_url = f"http://{local_ip}:{port}/api/videos/{video_id}/stream?token={token}"

    return {
        "video_id": video_id,
        "title": video.get("title", "Video"),
        "local_ip": local_ip,
        "port": port,
        "watch_url": watch_url,
        "stream_url": stream_url,
        "qr_url": qr_endpoint,
        "token": token,
        "pin": pin,
        "pin_enabled": pin_enabled,
        "encrypted": True,
        "duration": video.get("duration", 0),
        "file_size": video.get("file_size", 0),
        "file_format": video.get("file_format", "mp4")
    }


@router.get("/{video_id}/qr.svg")
async def get_video_qr_svg(
    video_id: str,
    request: Request,
    ip: Optional[str] = None,
    port: Optional[str] = "8000",
    p: Optional[str] = None,
    pin: Optional[str] = None,
    token: Optional[str] = None
):
    """Renders a crisp vector SVG QR code with embedded authorization PIN."""
    # Robust port parsing to handle query quirks cleanly without throwing 422
    clean_port = 8000
    raw_port = str(port or "8000").strip()
    if "?" in raw_port:
        parts = raw_port.split("?", 1)
        raw_port = parts[0]
        # Recover 'p' if inadvertently attached after question mark
        if not p and "=" in parts[1]:
            for param in parts[1].split("&"):
                if param.startswith("p="):
                    p = param.split("=", 1)[1]
    try:
        clean_port = int(raw_port)
    except (ValueError, TypeError):
        clean_port = 8000

    host_ip = ip.strip() if ip and ip.strip() else get_local_wifi_ip()
    v_pin, pin_enabled = get_or_create_pin(video_id)
    active_pin = (p or pin or v_pin).strip()

    if pin_enabled and active_pin:
        target_url = f"http://{host_ip}:{clean_port}/watch/{video_id}?p={active_pin}"
    else:
        target_url = f"http://{host_ip}:{clean_port}/watch/{video_id}"

    svg_content = generate_qr_svg(target_url, border=4, scale=8)

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-cache"}
    )


@router.post("/{video_id}/verify-pin")
async def verify_pin_endpoint(video_id: str, req: PinVerifyRequest, response: Response):
    """Verifies a submitted PIN and issues a cryptographically signed session token."""
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    success, token = verify_video_pin(video_id, req.pin)
    if not success or not token:
        raise HTTPException(status_code=401, detail="Incorrect PIN")

    response.set_cookie(
        key=f"vm_token_{video_id}",
        value=token,
        max_age=86400,
        httponly=True,
        samesite="lax"
    )
    return {"success": True, "token": token}


@router.post("/{video_id}/security-pin")
async def configure_pin_endpoint(video_id: str, req: PinConfigRequest, request: Request):
    """Allows desktop owner to update PIN or toggle PIN protection."""
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not is_client_localhost(request):
        raise HTTPException(status_code=403, detail="Security settings can only be altered from this machine.")

    pin, enabled = set_pin_config(video_id, req.pin, req.pin_enabled)
    token = generate_stream_token(video_id)
    return {"video_id": video_id, "pin": pin, "pin_enabled": enabled, "token": token}


@router.post("/{video_id}/regenerate-pin")
async def regenerate_pin_endpoint(video_id: str, request: Request):
    """Generates a fresh 4-digit random security PIN."""
    video = db_get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not is_client_localhost(request):
        raise HTTPException(status_code=403, detail="Security settings can only be altered from this machine.")

    import random
    new_pin = f"{random.randint(1000, 9999)}"
    set_pin_config(video_id, new_pin, pin_enabled=True)
    token = generate_stream_token(video_id)
    return {"video_id": video_id, "pin": new_pin, "pin_enabled": True, "token": token}
