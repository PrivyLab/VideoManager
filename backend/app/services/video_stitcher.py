import os
import shutil
import asyncio
import subprocess
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple

def get_ffmpeg_bin() -> str:
    bin_path = shutil.which("ffmpeg")
    if bin_path:
        return bin_path
    for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if os.path.exists(p):
            return p
    return "ffmpeg"

def get_ffprobe_bin() -> str:
    bin_path = shutil.which("ffprobe")
    if bin_path:
        return bin_path
    for p in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "/usr/bin/ffprobe"]:
        if os.path.exists(p):
            return p
    return "ffprobe"

class VideoStitcher:
    """
    Engine to stitch multiple downloaded video files into a single continuous video.
    Supports:
    - Fast stream copy (instant, lossless concat demuxer)
    - Smart re-encode (normalizes dimensions, codecs, and missing audio tracks)
    - Auto mode (tries fast stream copy, falls back to re-encode on incompatibility)
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._cancel_requested = False
        self.ffmpeg_bin = get_ffmpeg_bin()
        self.ffprobe_bin = get_ffprobe_bin()

    def cancel(self):
        self._cancel_requested = True

    def probe_video(self, file_path: Path) -> Dict[str, Any]:
        """Inspect video streams, audio streams, and duration via ffprobe."""
        cmd = [
            self.ffprobe_bin,
            "-v", "error",
            "-show_entries", "stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate",
            "-show_entries", "format=duration,size,bit_rate",
            "-of", "json",
            str(file_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            fmt = data.get("format", {})

            duration = float(fmt.get("duration", 0) or 0)
            size = int(fmt.get("size", 0) or file_path.stat().st_size)
            width = int(video_stream.get("width", 0) or 0) if video_stream else 0
            height = int(video_stream.get("height", 0) or 0) if video_stream else 0

            return {
                "file_path": str(file_path),
                "duration": duration,
                "size": size,
                "has_video": video_stream is not None,
                "has_audio": audio_stream is not None,
                "video_codec": video_stream.get("codec_name") if video_stream else None,
                "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}" if width and height else "unknown",
            }
        except Exception:
            return {
                "file_path": str(file_path),
                "duration": 0,
                "size": file_path.stat().st_size if file_path.exists() else 0,
                "has_video": True,
                "has_audio": True,
                "video_codec": None,
                "audio_codec": None,
                "width": 0,
                "height": 0,
                "resolution": "unknown",
            }

    async def generate_thumbnail(self, video_path: Path, thumb_path: Path) -> Optional[str]:
        """Generate a JPEG thumbnail at 1s timestamp."""
        try:
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", "00:00:01",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(thumb_path)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                return str(thumb_path)
        except Exception:
            pass
        return None

    async def _stitch_fast_copy(self, input_paths: List[Path], output_path: Path) -> bool:
        """Concatenate files using ffmpeg's concat demuxer with stream copy."""
        concat_file = output_path.parent / f"_concat_{self.job_id}.txt"
        try:
            with open(concat_file, "w", encoding="utf-8") as f:
                for path in input_paths:
                    escaped_path = str(path.resolve()).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(output_path)
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1024:
                return True
            return False
        finally:
            if concat_file.exists():
                try:
                    concat_file.unlink()
                except Exception:
                    pass

    async def _stitch_reencode(
        self,
        input_paths: List[Path],
        probed_info: List[Dict[str, Any]],
        output_path: Path,
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Concatenate files using ffmpeg concat filter, re-encoding video to standard H.264/AAC.
        Normalizes differing resolutions and handles missing audio tracks cleanly.
        """
        # Determine target resolution (max width and height or 1920x1080)
        max_w = max([p["width"] for p in probed_info if p.get("width")] or [1920])
        max_h = max([p["height"] for p in probed_info if p.get("height")] or [1080])
        # Ensure dimensions are even numbers (required by libx264)
        target_w = max_w + (max_w % 2)
        target_h = max_h + (max_h % 2)

        cmd = [self.ffmpeg_bin, "-y"]
        for p in input_paths:
            cmd.extend(["-i", str(p.resolve())])

        n = len(input_paths)
        filter_parts = []
        concat_inputs = []

        for i, info in enumerate(probed_info):
            # Scale with letterbox padding to preserve aspect ratio
            v_filter = (
                f"[{i}:v:0]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]"
            )
            filter_parts.append(v_filter)

            if info.get("has_audio"):
                filter_parts.append(f"[{i}:a:0]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]")
            else:
                # Generate silent audio matching duration of this clip
                clip_dur = max(info.get("duration", 1.0), 1.0)
                filter_parts.append(f"anullsrc=channel_layout=stereo:sample_rate=44100:d={clip_dur}[a{i}]")

            concat_inputs.append(f"[v{i}][a{i}]")

        filter_parts.append(f"{''.join(concat_inputs)}concat=n={n}:v=1:a=1[outv][outa]")
        filter_str = ";".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path)
        ])

        if progress_cb:
            progress_cb({
                "status": "merging",
                "progress": 30.0,
                "message": "Re-encoding and stitching video clips with ffmpeg..."
            })

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore")[-500:]
            raise RuntimeError(f"FFmpeg stitching failed: {err_msg}")

    async def stitch(
        self,
        input_paths: List[Path],
        output_dir: Path,
        output_filename: Optional[str] = None,
        mode: str = "auto",
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the stitching operation across multiple video files.
        """
        if len(input_paths) < 2:
            raise ValueError("Stitching requires at least two video files.")

        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_filename:
            output_filename = f"stitched_{self.job_id}.mp4"
        elif not output_filename.lower().endswith(".mp4"):
            output_filename = f"{output_filename}.mp4"

        output_path = output_dir / output_filename

        if progress_cb:
            progress_cb({
                "status": "merging",
                "progress": 15.0,
                "message": f"Analyzing {len(input_paths)} clips for stitching..."
            })

        # Probe all clips
        loop = asyncio.get_running_loop()
        probed = await asyncio.gather(
            *[loop.run_in_executor(None, self.probe_video, p) for p in input_paths]
        )

        total_input_duration = sum(p["duration"] for p in probed)
        all_same_res = len(set(p["resolution"] for p in probed)) == 1 and probed[0]["resolution"] != "unknown"
        all_same_codec = len(set(p["video_codec"] for p in probed)) == 1 and probed[0]["video_codec"] is not None

        success = False

        if mode in ("fast", "auto"):
            if progress_cb:
                progress_cb({
                    "status": "merging",
                    "progress": 35.0,
                    "message": "Attempting fast stream-copy merge..."
                })

            success = await self._stitch_fast_copy(input_paths, output_path)

        if not success:
            if mode == "fast":
                raise RuntimeError(
                    "Fast stream-copy merge failed because the selected videos have incompatible codecs, timebases, or resolutions. "
                    "Please try stitching with 'Smart Re-encode' mode."
                )

            # Auto fallback or explicit reencode
            if progress_cb:
                progress_cb({
                    "status": "merging",
                    "progress": 40.0,
                    "message": "Normalizing formats and stitching with ffmpeg re-encode..."
                })

            await self._stitch_reencode(input_paths, probed, output_path, progress_cb)
            success = output_path.exists() and output_path.stat().st_size > 0

        if not success:
            raise RuntimeError("Failed to produce stitched video.")

        if progress_cb:
            progress_cb({
                "status": "merging",
                "progress": 90.0,
                "message": "Generating thumbnail and finalizing video metadata..."
            })

        # Final probe on the output video
        final_info = await loop.run_in_executor(None, self.probe_video, output_path)

        # Generate thumbnail
        thumb_path = output_dir / f"{output_path.stem}_thumb.jpg"
        thumb_file = await self.generate_thumbnail(output_path, thumb_path)
        thumbnail_url = f"/api/videos/{self.job_id}/thumbnail" if thumb_file else ""

        return {
            "file_path": str(output_path),
            "file_size": final_info["size"],
            "duration": final_info["duration"] or total_input_duration,
            "resolution": final_info["resolution"],
            "file_format": "mp4",
            "thumbnail_url": thumbnail_url,
            "title": output_path.stem
        }

