import asyncio
import json
import subprocess

from app.services.video_stitcher import VideoStitcher, get_ffprobe_bin


def test_stitch_quality_presets_cap_resolution_and_preserve_orientation():
    landscape = [{"width": 2560, "height": 1440}]
    portrait = [{"width": 720, "height": 1280}]

    assert VideoStitcher._target_dimensions(landscape, "720p") == (1280, 720)
    assert VideoStitcher._target_dimensions(landscape, "480p") == (854, 480)
    assert VideoStitcher._target_dimensions(portrait, "480p") == (480, 854)
    assert VideoStitcher._target_dimensions(portrait, "1080p") == (720, 1280)


def test_source_quality_preserves_existing_max_dimensions():
    probed_info = [
        {"width": 1280, "height": 720},
        {"width": 720, "height": 1254},
    ]

    assert VideoStitcher._target_dimensions(probed_info, "source") == (1280, 1254)


def test_auto_mode_reencodes_compatible_clips_for_selected_quality(tmp_path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    _create_clip(first, "libx264", 1280, 720, 440)
    _create_clip(second, "libx264", 1280, 720, 660)

    result = asyncio.run(
        VideoStitcher("quality-preset-regression").stitch(
            input_paths=[first, second],
            output_dir=tmp_path,
            output_filename="stitched-480p.mp4",
            mode="auto",
            quality="480p",
        )
    )

    assert result["resolution"] == "854x480"


def _create_clip(path, video_codec, width, height, frequency):
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"testsrc=duration=1:size={width}x{height}:rate=30",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration=1",
            "-c:v", video_codec,
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_auto_stitch_reencodes_incompatible_video_streams(tmp_path):
    first = tmp_path / "h264.mp4"
    second = tmp_path / "mpeg4.mp4"
    _create_clip(first, "libx264", 320, 240, 440)
    _create_clip(second, "mpeg4", 640, 360, 660)

    stitcher = VideoStitcher("auto-stitch-regression")
    progress = []

    def report_progress(info):
        progress.append(info)

    result = asyncio.run(
        stitcher.stitch(
            input_paths=[first, second],
            output_dir=tmp_path,
            output_filename="stitched.mp4",
            mode="auto",
            progress_cb=report_progress,
        )
    )

    probe = subprocess.run(
        [
            get_ffprobe_bin(),
            "-v", "error",
            "-show_entries", "stream=codec_type,codec_name",
            "-of", "json",
            result["file_path"],
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert any(stream["codec_type"] == "video" and stream["codec_name"] == "h264" for stream in streams)
    assert any(stream["codec_type"] == "audio" and stream["codec_name"] == "aac" for stream in streams)
    assert result["duration"] >= 1.9
    assert any(info.get("message", "").startswith("Re-encoding clips:") for info in progress)

    subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-ss", "1.5",
            "-i", result["file_path"],
            "-map", "0:v:0",
            "-frames:v", "1",
            "-f", "null", "-",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
