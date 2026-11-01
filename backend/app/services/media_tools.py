import os
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.video_stitcher import get_ffmpeg_bin, get_ffprobe_bin, VideoStitcher

def probe_file(file_path: Path) -> Dict[str, Any]:
    ffprobe_bin = get_ffprobe_bin()
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height",
        "-show_entries", "format=duration,size,bit_rate",
        "-of", "json",
        str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        return {
            "duration": float(fmt.get("duration", 0) or 0),
            "size": int(fmt.get("size", 0) or (file_path.stat().st_size if file_path.exists() else 0)),
            "width": int(v_stream.get("width", 0) or 0) if v_stream else 0,
            "height": int(v_stream.get("height", 0) or 0) if v_stream else 0,
            "has_video": v_stream is not None,
        }
    except Exception:
        return {
            "duration": 0,
            "size": file_path.stat().st_size if file_path.exists() else 0,
            "width": 0,
            "height": 0,
            "has_video": True,
        }

async def extract_audio(
    source_path: Path,
    output_path: Path,
    audio_format: str = "mp3",
    bitrate: str = "192k"
) -> Dict[str, Any]:
    """
    Extract audio track from video file to MP3, M4A, or AAC.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source video file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()

    audio_format = audio_format.lower().strip()
    if audio_format not in ("mp3", "m4a", "aac", "wav"):
        audio_format = "mp3"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(source_path.resolve()),
        "-vn"
    ]

    if audio_format == "mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
    elif audio_format in ("m4a", "aac"):
        cmd.extend(["-c:a", "aac", "-b:a", bitrate])
    elif audio_format == "wav":
        cmd.extend(["-c:a", "pcm_s16le"])

    cmd.append(str(output_path.resolve()))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="ignore")[-400:]
        raise RuntimeError(f"FFmpeg audio extraction failed: {err_msg}")

    info = probe_file(output_path)

    return {
        "file_path": str(output_path),
        "file_size": info["size"],
        "duration": info["duration"],
        "file_format": audio_format,
    }

async def compress_video(
    source_path: Path,
    output_path: Path,
    preset: str = "balanced",  # "light", "balanced", "discord"
    resolution: str = "same"   # "same", "1080p", "720p", "480p"
) -> Dict[str, Any]:
    """
    Compress a large video down using H.264 CRF encoding.
    - light: CRF 24 (~30% smaller, imperceptible loss)
    - balanced: CRF 28 (~50-60% smaller, ideal for web)
    - discord: CRF 30 + 720p (~80% smaller, fits in WhatsApp/Discord/Slack)
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()

    crf = "28"
    speed_preset = "fast"
    audio_bitrate = "128k"

    if preset == "light":
        crf = "24"
        audio_bitrate = "160k"
    elif preset == "discord":
        crf = "30"
        audio_bitrate = "96k"
        if resolution == "same":
            resolution = "720p"

    scale_filter = None
    if resolution == "1080p":
        scale_filter = "scale=-2:1080"
    elif resolution == "720p":
        scale_filter = "scale=-2:720"
    elif resolution == "480p":
        scale_filter = "scale=-2:480"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(source_path.resolve()),
        "-c:v", "libx264",
        "-crf", crf,
        "-preset", speed_preset,
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-movflags", "+faststart"
    ]

    if scale_filter:
        cmd.extend(["-vf", scale_filter])

    cmd.append(str(output_path.resolve()))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="ignore")[-400:]
        raise RuntimeError(f"FFmpeg compression failed: {err_msg}")

    info = probe_file(output_path)
    res_str = f"{info['width']}x{info['height']}" if info['width'] and info['height'] else "1080p"

    thumb_path = output_path.parent / f"{output_path.stem}_thumb.jpg"
    stitcher = VideoStitcher("thumb")
    await stitcher.generate_thumbnail(output_path, thumb_path)

    return {
        "file_path": str(output_path),
        "file_size": info["size"],
        "duration": info["duration"],
        "resolution": res_str,
        "thumbnail_url": f"/api/videos/{output_path.stem.split('_')[0]}/thumbnail" if thumb_path.exists() else "",
    }

async def create_gif(
    source_path: Path,
    output_path: Path,
    start_time: float = 0.0,
    duration: float = 5.0,
    fps: int = 15,
    width: int = 480
) -> Dict[str, Any]:
    """
    Generate an animated GIF using 2-pass palettegen filter for crisp colors and small file size.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source video file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()

    duration = min(max(duration, 1.0), 30.0)  # cap between 1 and 30 seconds
    fps = min(max(fps, 10), 30)
    width = min(max(width, 240), 800)

    # 2-pass high quality palette filter
    filter_complex = f"[0:v]fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", str(source_path.resolve()),
        "-filter_complex", filter_complex,
        str(output_path.resolve())
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode("utf-8", errors="ignore")[-400:]
        raise RuntimeError(f"FFmpeg GIF creation failed: {err_msg}")

    info = probe_file(output_path)

    return {
        "file_path": str(output_path),
        "file_size": info["size"],
        "duration": duration,
        "resolution": f"{width}px",
        "file_format": "gif",
    }

async def trim_video(
    source_path: Path,
    output_path: Path,
    start_time: float,
    end_time: float,
    mode: str = "fast"
) -> Dict[str, Any]:
    """
    Trim a video file between start_time and end_time.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source video file not found: {source_path}")
    if start_time < 0:
        start_time = 0
    if end_time <= start_time:
        raise ValueError("End time must be greater than start time.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()
    duration_segment = end_time - start_time

    if mode == "fast":
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", str(source_path.resolve()),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            str(output_path.resolve())
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
            mode = "reencode"

    if mode == "reencode":
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", str(source_path.resolve()),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path.resolve())
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore")[-400:]
            raise RuntimeError(f"FFmpeg trim failed: {err_msg}")

    info = probe_file(output_path)
    res_str = f"{info['width']}x{info['height']}" if info['width'] and info['height'] else "1080p"

    thumb_path = output_path.parent / f"{output_path.stem}_thumb.jpg"
    stitcher = VideoStitcher("thumb")
    await stitcher.generate_thumbnail(output_path, thumb_path)

    return {
        "file_path": str(output_path),
        "file_size": info["size"],
        "duration": info["duration"] or duration_segment,
        "resolution": res_str,
        "thumbnail_url": f"/api/videos/{output_path.stem.split('_')[0]}/thumbnail" if thumb_path.exists() else "",
    }
