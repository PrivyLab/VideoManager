import logging
import subprocess
import shutil
from functools import lru_cache
from typing import Dict, Any, List, Optional

logger = logging.getLogger("hardware_accel")

def get_ffmpeg_bin() -> str:
    bin_path = shutil.which("ffmpeg")
    if bin_path:
        return bin_path
    for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        import os
        if os.path.exists(p):
            return p
    return "ffmpeg"

@lru_cache(maxsize=1)
def detect_hardware_encoder() -> Dict[str, Any]:
    """
    Tests hardware acceleration availability at runtime.
    Priority order:
    1. Apple VideoToolbox (macOS Apple Silicon / Intel GPU)
    2. NVIDIA NVENC (Linux / Windows with NVIDIA GPU)
    3. Intel QuickSync / QSV (Intel CPU with Iris/Xe GPU)
    4. VA-API (Linux generic GPU acceleration)
    5. libx264 (Universal software CPU fallback)
    """
    ffmpeg_bin = get_ffmpeg_bin()
    candidates = [
        {"encoder": "h264_videotoolbox", "type": "gpu", "platform": "apple",  "name": "Apple VideoToolbox (GPU/Media Engine)"},
        {"encoder": "h264_nvenc",        "type": "gpu", "platform": "nvidia", "name": "NVIDIA NVENC (GPU)"},
        {"encoder": "h264_qsv",          "type": "gpu", "platform": "intel",  "name": "Intel QuickSync (GPU)"},
        {"encoder": "h264_vaapi",        "type": "gpu", "platform": "vaapi",  "name": "Linux VA-API (GPU)"},
    ]

    for cand in candidates:
        cmd = [
            ffmpeg_bin,
            "-v", "error",
            "-f", "lavfi",
            "-i", "nullsrc=s=64x64:r=30",
            "-frames:v", "1",
            "-c:v", cand["encoder"],
            "-f", "null",
            "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=3)
            if res.returncode == 0:
                logger.info(f"Device selected: {cand['name']} (encoder={cand['encoder']})")
                return cand
        except Exception:
            continue

    logger.info("Device selected: CPU fallback (encoder=libx264)")
    return {"encoder": "libx264", "type": "cpu", "platform": "generic", "name": "Software libx264 (CPU)"}

def get_video_encode_args(
    target_height: Optional[int] = None,
    quality_preset: str = "balanced",
    crf: str = "23"
) -> List[str]:
    """
    Returns optimal FFmpeg CLI video encoding flags dynamically tailored
    to the active hardware encoder (GPU) or software CPU fallback.
    """
    hw_info = detect_hardware_encoder()
    encoder = hw_info["encoder"]

    if encoder == "h264_videotoolbox":
        # Apple VideoToolbox Hardware Encoder
        # Bitrate mapping based on target resolution & preset
        h = target_height or 1080
        if quality_preset == "light":
            bitrate = "6000k" if h >= 1080 else ("3500k" if h >= 720 else "1800k")
        elif quality_preset == "discord":
            bitrate = "1200k" if h >= 720 else "800k"
        else:  # balanced / standard / stitch
            if h >= 1080:
                bitrate = "4500k"
            elif h >= 720:
                bitrate = "2500k"
            elif h >= 480:
                bitrate = "1200k"
            else:
                bitrate = "800k"

        return [
            "-c:v", "h264_videotoolbox",
            "-b:v", bitrate,
            "-pix_fmt", "yuv420p",
            "-prio_speed", "1",
            "-realtime", "0"
        ]

    elif encoder == "h264_nvenc":
        # NVIDIA NVENC Hardware Encoder (optimized for throughput)
        return [
            "-c:v", "h264_nvenc",
            "-pix_fmt", "yuv420p",
            "-preset", "p2",
            "-cq", crf
        ]

    elif encoder == "h264_qsv":
        # Intel QuickSync Hardware Encoder
        return [
            "-c:v", "h264_qsv",
            "-pix_fmt", "yuv420p",
            "-global_quality", crf
        ]

    else:
        # Standard software CPU fallback - veryfast preset uses all CPU threads
        speed = "veryfast"
        if quality_preset == "light":
            speed = "ultrafast"
        return [
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", speed,
            "-crf", crf,
            "-threads", "0"
        ]
