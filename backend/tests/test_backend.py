import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db, db_create_video, db_get_video, db_update_video, db_get_all_videos, db_delete_video
from app.services.chunk_engine import ChunkEngine
from app.config import get_configured_download_dir, set_configured_download_dir
from app.services.video_stitcher import VideoStitcher
from app.services.media_tools import extract_audio, compress_video, create_gif, trim_video

def test_db_operations():
    init_db()
    test_id = "test_vid_123"
    db_create_video({
        "id": test_id,
        "url": "https://example.com/test.mp4",
        "title": "Test Video Title",
        "duration": 120.5,
        "file_path": "/tmp/test.mp4",
        "file_size": 1048576,
        "file_format": "mp4",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "resolution": "1920x1080",
        "status": "completed",
        "progress": 100.0,
        "speed": "5.2 MB/s",
        "eta": "0s",
        "error_message": "",
        "downloader_type": "chunked",
        "chunks_total": 4,
        "chunks_completed": 4,
        "created_at": "2026-11-01T20:00:00",
        "completed_at": "2026-11-01T20:00:10"
    })

    video = db_get_video(test_id)
    assert video is not None
    assert video["title"] == "Test Video Title"

    db_update_video(test_id, {"title": "Updated Title"})
    video_updated = db_get_video(test_id)
    assert video_updated["title"] == "Updated Title"

    all_vids = db_get_all_videos()
    assert any(v["id"] == test_id for v in all_vids)

    db_delete_video(test_id)
    assert db_get_video(test_id) is None
    print("Database operations test: PASSED")

def test_chunk_engine_merging():
    import asyncio
    engine = ChunkEngine("unit_test")
    
    chunk_0 = engine.work_dir / "chunk_0.part"
    chunk_1 = engine.work_dir / "chunk_1.part"
    output_file = engine.work_dir / "merged_output.bin"

    with open(chunk_0, "wb") as f:
        f.write(b"HELLO ")
    with open(chunk_1, "wb") as f:
        f.write(b"WORLD!")

    async def run_merge():
        await engine.merge_chunks([chunk_0, chunk_1], output_file)

    asyncio.run(run_merge())

    assert output_file.exists()
    with open(output_file, "rb") as f:
        content = f.read()
    assert content == b"HELLO WORLD!"
    engine.cleanup()
    print("Chunk engine merge test: PASSED")

def test_download_folder_configuration():
    test_folder = Path("/tmp/videomanager_custom_downloads")
    set_configured_download_dir(str(test_folder))
    configured = get_configured_download_dir()
    assert str(configured) == str(test_folder.resolve())
    assert test_folder.exists()
    print("Download folder configuration test: PASSED")

def test_video_stitching():
    import asyncio
    import subprocess
    
    # Generate 2 minimal test clips using ffmpeg
    clip1 = Path("/tmp/test_stitch_1.mp4")
    clip2 = Path("/tmp/test_stitch_2.mp4")
    out_dir = Path("/tmp/test_stitch_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    cmd1 = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(clip1)]
    cmd2 = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30", "-f", "lavfi", "-i", "sine=frequency=500:duration=1", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(clip2)]
    
    subprocess.run(cmd1, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    stitcher = VideoStitcher("test_job")
    
    async def run_stitch():
        return await stitcher.stitch(
            input_paths=[clip1, clip2],
            output_dir=out_dir,
            output_filename="merged_test.mp4",
            mode="auto"
        )
        
    res = asyncio.run(run_stitch())
    assert Path(res["file_path"]).exists()
    assert res["file_size"] > 1000
    assert res["duration"] >= 1.9
    
    # Cleanup
    clip1.unlink(missing_ok=True)
    clip2.unlink(missing_ok=True)
    Path(res["file_path"]).unlink(missing_ok=True)
    thumb = out_dir / "merged_test_thumb.jpg"
    thumb.unlink(missing_ok=True)
    print("Video stitching test: PASSED")

def test_media_tools():
    import asyncio
    import subprocess

    source = Path("/tmp/test_source_media.mp4")
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=30", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(source)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    out_mp3 = Path("/tmp/test_out.mp3")
    out_compressed = Path("/tmp/test_out_comp.mp4")
    out_gif = Path("/tmp/test_out.gif")

    async def run_tools():
        res_mp3 = await extract_audio(source, out_mp3, audio_format="mp3")
        res_comp = await compress_video(source, out_compressed, preset="balanced")
        res_gif = await create_gif(source, out_gif, start_time=0.0, duration=1.0, fps=12, width=320)
        return res_mp3, res_comp, res_gif

    res_mp3, res_comp, res_gif = asyncio.run(run_tools())

    assert out_mp3.exists() and out_mp3.stat().st_size > 500
    assert out_compressed.exists() and out_compressed.stat().st_size > 500
    assert out_gif.exists() and out_gif.stat().st_size > 500

    # Cleanup
    source.unlink(missing_ok=True)
    out_mp3.unlink(missing_ok=True)
    out_compressed.unlink(missing_ok=True)
    out_gif.unlink(missing_ok=True)
    Path("/tmp/test_out_comp_thumb.jpg").unlink(missing_ok=True)
    print("Media Tools (Extract Audio, Compress, GIF) test: PASSED")

def test_video_trimmer():
    import asyncio
    import subprocess
    from app.services.ytdlp_downloader import parse_time_seconds

    # Test time parser
    assert parse_time_seconds("01:30") == 90.0
    assert parse_time_seconds("00:45") == 45.0
    assert parse_time_seconds("90") == 90.0
    assert parse_time_seconds("01:10:00") == 4200.0
    assert parse_time_seconds("") is None
    assert parse_time_seconds(None) is None

    # Generate a 4-second test video
    source = Path("/tmp/test_source_trim.mp4")
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=30", "-f", "lavfi", "-i", "sine=frequency=600:duration=4", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(source)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    out_fast = Path("/tmp/test_trim_fast.mp4")
    out_reencode = Path("/tmp/test_trim_reencode.mp4")
    out_audio = Path("/tmp/test_trim_audio.mp3")

    async def run_trim_tests():
        res_fast = await trim_video(source, out_fast, start_time=1.0, end_time=3.0, mode="fast")
        res_reencode = await trim_video(source, out_reencode, start_time=0.5, end_time=2.5, mode="reencode")
        res_audio = await trim_video(source, out_audio, start_time=1.0, end_time=2.0, extract_audio=True)
        return res_fast, res_reencode, res_audio

    res_fast, res_reencode, res_audio = asyncio.run(run_trim_tests())

    assert out_fast.exists() and out_fast.stat().st_size > 100
    assert out_reencode.exists() and out_reencode.stat().st_size > 100
    assert out_audio.exists() and out_audio.stat().st_size > 100
    assert res_audio["file_format"] == "mp3"

    # Cleanup
    source.unlink(missing_ok=True)
    out_fast.unlink(missing_ok=True)
    out_reencode.unlink(missing_ok=True)
    out_audio.unlink(missing_ok=True)
    Path("/tmp/test_trim_fast_thumb.jpg").unlink(missing_ok=True)
    Path("/tmp/test_trim_reencode_thumb.jpg").unlink(missing_ok=True)
    print("Video Trimmer (Instant Cut, Frame-Accurate Cut, Audio Snippet) test: PASSED")

def test_batch_and_playlist_queuing():
    import asyncio
    from app.services.download_manager import download_manager
    from app.models import DownloadRequest, BatchDownloadRequest, BatchDownloadItem

    async def run_batch_test():
        # Test queuing 3 download requests
        reqs = [
            DownloadRequest(url=f"https://example.com/video_{i}.mp4", custom_title=f"Bulk Episode {i}")
            for i in range(1, 4)
        ]
        ids = []
        for r in reqs:
            vid_id = await download_manager.start_download(r)
            ids.append(vid_id)

        assert len(ids) == 3
        # Check that videos are saved in DB
        for vid in ids:
            record = db_get_video(vid)
            assert record is not None
            assert record["status"] in ("queued", "downloading", "failed", "cancelled")
            # Cancel test tasks cleanly
            await download_manager.cancel_download(vid)
            db_delete_video(vid)

    asyncio.run(run_batch_test())
    print("Batch & Playlist Queue Manager test: PASSED")

if __name__ == "__main__":
    test_db_operations()
    test_chunk_engine_merging()
    test_download_folder_configuration()
    test_video_stitching()
    test_media_tools()
    test_video_trimmer()
    test_batch_and_playlist_queuing()
    print("ALL TESTS PASSED SUCCESSFULLY!")
