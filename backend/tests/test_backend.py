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
    from app.config import ROOT_DIR, BASE_DIR

    # 1. When .env is NOT present, configuration comes from settings.json
    test_folder = Path("/tmp/videomanager_custom_downloads")
    set_configured_download_dir(str(test_folder))
    configured = get_configured_download_dir()
    assert str(configured) == str(test_folder.resolve())
    assert test_folder.exists()

    # 2. When .env IS present, take download directory from .env instead of settings.json
    env_target_file = BASE_DIR / ".env"
    env_folder = Path("/tmp/videomanager_from_env_downloads")
    try:
        with open(env_target_file, "w") as f:
            f.write(f"DOWNLOAD_DIR={env_folder}\n")

        # Must take from .env instead of settings.json
        configured_env = get_configured_download_dir()
        assert str(configured_env) == str(env_folder.resolve())
        assert env_folder.exists()
    finally:
        if env_target_file.exists():
            env_target_file.unlink()

    # 3. After .env is removed, it seamlessly falls back to settings.json
    reverted = get_configured_download_dir()
    assert str(reverted) == str(test_folder.resolve())

    print("Download folder configuration (.env vs settings.json) test: PASSED")

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

def test_qr_and_mobile_stream():
    from app.services.qr_generator import get_local_wifi_ip, generate_qr_svg

    ip = get_local_wifi_ip()
    assert ip and len(ip.split(".")) == 4

    test_url = f"http://{ip}:8000/watch/test_mobile_stream"
    svg = generate_qr_svg(test_url)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "fill=\"#000000\"" in svg
    print("QR Code & Wi-Fi Mobile Streaming test: PASSED")

def test_byte_range_mobile_seeking():
    from starlette.testclient import TestClient
    from app.main import app
    from app.database import db_create_video, db_delete_video
    from app.services.faststart import is_mp4_faststart

    client = TestClient(app)
    test_id = "test_seek_video"

    # Create a 2000-byte test file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        dummy_data = b"M4V " + (b"0123456789" * 199) + b"END!"
        tf.write(dummy_data)
        tf_path = tf.name

    db_create_video({
        "id": test_id,
        "url": "https://example.com/test.mp4",
        "title": "Mobile Seek Test Video",
        "file_path": tf_path,
        "file_size": len(dummy_data),
        "status": "completed",
        "created_at": "2026-11-01T00:00:00Z",
    })

    try:
        # 1. HEAD request (mobile Safari probes this before playback)
        r_head = client.head(f"/api/videos/{test_id}/stream")
        assert r_head.status_code == 200, f"HEAD request failed: {r_head.status_code}"
        assert r_head.headers.get("accept-ranges") == "bytes"
        assert int(r_head.headers.get("content-length", 0)) == len(dummy_data)

        # 2. Safari initial probe (Range: bytes=0-1)
        r_probe = client.get(f"/api/videos/{test_id}/stream", headers={"Range": "bytes=0-1"})
        assert r_probe.status_code == 206
        assert r_probe.headers.get("content-range") == f"bytes 0-1/{len(dummy_data)}"
        assert len(r_probe.content) == 2

        # 3. Seeking forward (Range: bytes=500-999)
        r_seek = client.get(f"/api/videos/{test_id}/stream", headers={"Range": "bytes=500-999"})
        assert r_seek.status_code == 206
        assert r_seek.headers.get("content-range") == f"bytes 500-999/{len(dummy_data)}"
        assert len(r_seek.content) == 500
        assert r_seek.content == dummy_data[500:1000]

        # 4. Open-ended seek (Range: bytes=1500-)
        r_open = client.get(f"/api/videos/{test_id}/stream", headers={"Range": "bytes=1500-"})
        assert r_open.status_code == 206
        assert r_open.headers.get("content-range") == f"bytes 1500-{len(dummy_data)-1}/{len(dummy_data)}"
        assert len(r_open.content) == len(dummy_data) - 1500
        assert r_open.content == dummy_data[1500:]

        # 5. Suffix range for moov atom inspection (Range: bytes=-100)
        r_suffix = client.get(f"/api/videos/{test_id}/stream", headers={"Range": "bytes=-100"})
        assert r_suffix.status_code == 206
        expected_start = len(dummy_data) - 100
        assert r_suffix.headers.get("content-range") == f"bytes {expected_start}-{len(dummy_data)-1}/{len(dummy_data)}"
        assert len(r_suffix.content) == 100
        assert r_suffix.content == dummy_data[-100:]

        # 6. Mobile HTML watch page contains touch seek controls
        r_watch = client.get(f"/watch/{test_id}")
        assert r_watch.status_code == 200
        assert "seekBy" in r_watch.text
        assert "touch-controls" in r_watch.text
        assert "preload=\"auto\"" in r_watch.text

        print("HTTP Byte-Range Mobile Seeking test: PASSED")
    finally:
        db_delete_video(test_id)
        if os.path.exists(tf_path):
            os.unlink(tf_path)

def test_stream_encryption_and_pin_security():
    from starlette.testclient import TestClient
    from app.main import app
    from app.database import db_create_video, db_delete_video
    from app.services.stream_auth import (
        generate_stream_token,
        verify_stream_token,
        get_or_create_pin,
        verify_video_pin,
        set_pin_config,
    )
    import tempfile

    test_id = "test_enc_video"
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"M4V " + (b"secure_stream_bytes_" * 50))
        tf_path = tf.name

    db_create_video({
        "id": test_id,
        "url": "https://example.com/secure.mp4",
        "title": "Encrypted Test Video",
        "file_path": tf_path,
        "file_size": os.path.getsize(tf_path),
        "status": "completed",
        "created_at": "2026-11-01T00:00:00Z",
    })

    try:
        # 1. Cryptographic HMAC Token generation & tamper detection
        token = generate_stream_token(test_id)
        assert verify_stream_token(token, test_id) is True
        assert verify_stream_token(token, "wrong_video_id") is False
        assert verify_stream_token(token + "corrupt", test_id) is False

        # 2. PIN generation and verification
        pin, enabled = get_or_create_pin(test_id)
        assert len(pin) >= 4 and pin.isdigit()
        assert enabled is True

        # Incorrect PIN fails
        valid, _ = verify_video_pin(test_id, "0000_wrong")
        assert valid is False

        # Correct PIN succeeds and returns a valid cryptographic token
        valid, issued_token = verify_video_pin(test_id, pin)
        assert valid is True
        assert verify_stream_token(issued_token, test_id) is True

        client = TestClient(app)

        # 3. Share link endpoint returns token and PIN metadata
        share_res = client.get(f"/api/videos/{test_id}/share-link")
        assert share_res.status_code == 200
        data = share_res.json()
        assert data["encrypted"] is True
        assert "token" in data
        assert "pin" in data
        assert "p=" in data["watch_url"]

        # 4. PIN verification API endpoint
        v_res = client.post(f"/api/videos/{test_id}/verify-pin", json={"pin": pin})
        assert v_res.status_code == 200
        assert v_res.json()["success"] is True
        assert "token" in v_res.json()

        # Wrong PIN returns 401
        v_fail = client.post(f"/api/videos/{test_id}/verify-pin", json={"pin": "99999999"})
        assert v_fail.status_code == 401

        # 5. Mobile Watch page with ?p={pin} auto-authenticates from QR code
        w_res_pin = client.get(f"/watch/{test_id}?p={pin}")
        assert w_res_pin.status_code == 200
        assert "player" in w_res_pin.text
        assert "Encrypted Wi-Fi Stream" in w_res_pin.text

        # 6. Mobile Watch page with token renders player
        w_res = client.get(f"/watch/{test_id}?token={token}")
        assert w_res.status_code == 200
        assert "player" in w_res.text
        assert "Encrypted Wi-Fi Stream" in w_res.text

        # 6. Stream with token query param succeeds
        s_res = client.get(f"/api/videos/{test_id}/stream?token={token}")
        assert s_res.status_code == 200
        assert b"secure_stream_bytes" in s_res.content

        print("Wi-Fi Stream Cryptographic Encryption & PIN Security test: PASSED")
    finally:
        db_delete_video(test_id)
        if os.path.exists(tf_path):
            os.unlink(tf_path)

def test_single_direct_video_stream():
    import asyncio
    import httpx
    from app.services.download_manager import extract_filename_from_url, sanitize_media_filename

    # 1. Test clean filename extraction for direct media URLs
    sample_direct_url = "https://cdn.example.com/storage/1/60/sample_direct_video.mp4"
    extracted = extract_filename_from_url(sample_direct_url)
    assert extracted == "sample_direct_video.mp4"

    dirty_title = 'My: Cool "Video" <123>?*'
    sanitized = sanitize_media_filename(dirty_title)
    assert sanitized == "My Cool Video 123"

    # 2. Mock HTTP server that DOES NOT support Range requests (returns 200, no accept-ranges)
    video_bytes = b"\x00\x00\x00 ftypisom" + b"A" * 10240

    def mock_handler(request: httpx.Request):
        # Emulate servers or CDNs without range support
        # HEAD returns 405 Method Not Allowed
        if request.method == "HEAD":
            return httpx.Response(405, headers={"Allow": "GET"})
        if request.method == "GET":
            # Normal GET response with no Accept-Ranges header
            return httpx.Response(
                200,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(video_bytes))
                },
                content=video_bytes
            )
        return httpx.Response(400)

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    test_id = "test_single_stream_vid"
    engine = ChunkEngine(test_id, client=mock_client)
    out_dir = Path("/tmp/test_single_stream_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = "sample_direct_video.mp4"

    progress_events = []
    def on_progress(p):
        progress_events.append(p)

    async def run_direct_download():
        return await engine.download_with_chunking(
            url=sample_direct_url,
            output_filename=out_file,
            num_chunks=4,
            output_dir=out_dir,
            progress_callback=on_progress
        )

    res_path = asyncio.run(run_direct_download())
    assert res_path.exists()
    assert res_path.stat().st_size == len(video_bytes)
    with open(res_path, "rb") as f:
        assert f.read() == video_bytes

    # Ensure progress callback was called and completed
    assert any(p.get("status") == "completed" for p in progress_events)
    # Ensure temporary work dir was cleaned up
    assert not engine.work_dir.exists()

    if res_path.exists():
        res_path.unlink()

    print("Single direct video stream (non-range) test: PASSED")

def test_desktop_security_boundaries():
    from starlette.testclient import TestClient
    from app.main import app

    # Simulated phone client on local Wi-Fi (IP: 192.168.1.55)
    phone = TestClient(app, client=("192.168.1.55", 54321))

    # 1. Phone attempting to access Desktop SPA Dashboard -> 403 HTML Forbidden
    r_root = phone.get("/")
    assert r_root.status_code == 403
    assert "Desktop Only Area" in r_root.text

    # 2. Phone attempting to browse host file system -> 403 Forbidden
    r_browse = phone.get("/api/system/browse-folders")
    assert r_browse.status_code == 403
    assert "Access denied" in r_browse.json()["detail"]

    # 3. Phone attempting to view or change download directory -> 403 Forbidden
    r_settings = phone.get("/api/system/settings")
    assert r_settings.status_code == 403

    r_set_post = phone.post("/api/system/settings", json={"download_folder": "/tmp"})
    assert r_set_post.status_code == 403

    # 4. Phone attempting to list entire video library -> 403 Forbidden
    r_vids = phone.get("/api/videos")
    assert r_vids.status_code == 403

    # 5. Phone attempting to trigger downloads on laptop -> 403 Forbidden
    r_dl = phone.post("/api/downloads", json={"url": "https://example.com/test.mp4"})
    assert r_dl.status_code == 403

    # 6. Localhost Desktop user retains full access
    desktop = TestClient(app, client=("127.0.0.1", 54321))
    r_desk_sys = desktop.get("/api/system/settings")
    assert r_desk_sys.status_code == 200
    assert "download_folder" in r_desk_sys.json()

    print("Desktop Security & Wi-Fi Boundaries test: PASSED")

def test_video_link_finder():
    import asyncio
    import httpx
    from starlette.testclient import TestClient
    from app.main import app
    from app.services.video_link_finder import VideoLinkFinder, MediaHTMLParser

    # 1. Test Stealth Headers
    target_url = "https://news.example.com/tech/new-video-story"
    headers = VideoLinkFinder.build_stealth_headers(target_url)
    assert "Mozilla/5.0" in headers["User-Agent"]
    assert "Chromium" in headers["Sec-Ch-Ua"]
    assert headers["Referer"] == "https://news.example.com/"
    assert headers["Sec-Fetch-Mode"] == "navigate"

    # 2. Test MediaHTMLParser with diverse video embeds & streaming manifests
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Article with Embedded Media</title>
      <meta property="og:title" content="Awesome Tech Story">
      <meta property="og:image" content="https://cdn.example.com/poster.jpg">
      <meta property="og:video" content="/videos/og_preview.mp4">
      <meta name="twitter:player:stream" content="https://cdn.example.com/twitter_stream.m3u8">
    </head>
    <body>
      <h1>Article Title</h1>
      <video poster="/poster2.jpg">
        <source src="/media/clip_1080p.mp4" type="video/mp4">
        <source src="https://stream.example.com/master.m3u8" type="application/x-mpegURL">
      </video>
      <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" width="560" height="315"></iframe>
      <a href="/downloads/full_episode.mkv">Direct Download MKV</a>
      <script>
        var playerConfig = {
          file: "https://secure.cdn.example.com/jwplayer_stream.mp4",
          hls: "https://secure.cdn.example.com/hls/live.m3u8"
        };
      </script>
    </body>
    </html>
    """

    parser = MediaHTMLParser(base_url="https://news.example.com/tech/new-video-story")
    parser.feed(sample_html)

    urls_found = [item["url"] for item in parser.media_items]
    sources_found = [item["source"] for item in parser.media_items]

    assert "https://news.example.com/videos/og_preview.mp4" in urls_found
    assert "https://cdn.example.com/twitter_stream.m3u8" in urls_found
    assert "https://news.example.com/media/clip_1080p.mp4" in urls_found
    assert "https://stream.example.com/master.m3u8" in urls_found
    assert "https://www.youtube.com/embed/dQw4w9WgXcQ" in urls_found
    assert "https://news.example.com/downloads/full_episode.mkv" in urls_found
    assert "https://secure.cdn.example.com/jwplayer_stream.mp4" in urls_found
    assert "https://secure.cdn.example.com/hls/live.m3u8" in urls_found

    # 3. Test Proxy resolution
    assert VideoLinkFinder.resolve_proxy("direct") is None
    assert VideoLinkFinder.resolve_proxy("warp") is not None
    assert VideoLinkFinder.resolve_proxy("tor") is not None
    assert VideoLinkFinder.resolve_proxy("custom", "http://127.0.0.1:8888") == "http://127.0.0.1:8888"

    # 4. Test API Endpoint via TestClient (Localhost desktop)
    # Mock httpx GET for the endpoint test
    def mock_fetch(request: httpx.Request):
        return httpx.Response(200, text=sample_html, request=request)

    transport = httpx.MockTransport(mock_fetch)

    # Directly run find_links with mock client
    async def run_finder_test():
        orig_async_client = httpx.AsyncClient
        try:
            httpx.AsyncClient = lambda **kwargs: orig_async_client(transport=transport, **kwargs)
            res = await VideoLinkFinder.find_links(
                url="https://news.example.com/tech/new-video-story",
                routing_mode="direct",
                use_stealth=True
            )
            assert res["total_found"] >= 7
            assert res["stealth_used"] is True
            assert res["page_title"] == "Awesome Tech Story"
        finally:
            httpx.AsyncClient = orig_async_client

    asyncio.run(run_finder_test())

    # 5. Localhost vs Non-localhost security on /api/downloads/find-links
    desktop_client = TestClient(app, client=("127.0.0.1", 54321))
    phone_client = TestClient(app, client=("192.168.1.55", 54321))

    # Phone is rejected with 403
    r_phone = phone_client.post("/api/downloads/find-links", json={"url": "https://example.com"})
    assert r_phone.status_code == 403

    # 6. Test Page with 9 .mp4 links in various formats (nested <a><img>, data attributes, JS JSON)
    nine_vids_html = """
    <html>
    <head><title>Archive Thread 12345</title></head>
    <body>
      <div class="post" id="p1">
        <a class="file" href="/storage/1/vid1.mp4"><img src="/storage/1/thumb1.jpg" alt="Video One"></a>
      </div>
      <div class="post" id="p2">
        <a class="file" href="//cdn.example.com/storage/2/vid2.mp4?token=xyz"><img src="//cdn.example.com/storage/2/thumb2.jpg"></a>
      </div>
      <div class="post" id="p3">
        <a href="https://cdn.example.com/storage/3/vid3.mp4">Download Vid 3</a>
      </div>
      <div class="post" id="p4" data-video="/storage/4/vid4.mp4" data-thumb="/storage/4/thumb4.jpg">
        <span>Post 4 content</span>
      </div>
      <div class="post" id="p5">
        <video src="/storage/5/vid5.mp4" poster="/storage/5/poster5.jpg"></video>
      </div>
      <div class="post" id="p6">
        <video><source src="/storage/6/vid6.mp4" type="video/mp4"></video>
      </div>
      <div class="post" id="p7">
        <a href="/storage/7/vid7.mp4"><img data-src="/storage/7/thumb7.webp" alt="Vid 7"></a>
      </div>
      <script>
        var extra = {
          "items": [
            {"url": "https:\\/\\/cdn.example.com\\/storage\\/8\\/vid8.mp4", "thumb": "https:\\/\\/cdn.example.com\\/storage\\/8\\/t8.jpg"},
            {"file": "https:\\/\\/cdn.example.com\\/storage\\/9\\/vid9.mp4"}
          ]
        };
      </script>
    </body>
    </html>
    """

    def mock_fetch_9(request: httpx.Request):
        return httpx.Response(200, text=nine_vids_html, request=request)

    async def run_nine_vids_test():
        orig_async_client = httpx.AsyncClient
        try:
            httpx.AsyncClient = lambda **kwargs: orig_async_client(transport=httpx.MockTransport(mock_fetch_9), **kwargs)
            res = await VideoLinkFinder.find_links(
                url="https://example.com/thread/12345",
                routing_mode="direct",
                use_stealth=True
            )
            assert res["total_found"] == 9, f"Expected 9 links, got {res['total_found']}: {[l['url'] for l in res['links']]}"
            # Ensure thumbnails are associated
            assert any(l["thumbnail"].endswith("thumb1.jpg") for l in res["links"])
        finally:
            httpx.AsyncClient = orig_async_client

    asyncio.run(run_nine_vids_test())

    # 7. Test Homepage Video Cards with Thumbnails
    homepage_html = """
    <html>
    <head><title>VideoShare Homepage</title></head>
    <body>
      <div class="video-grid">
        <div class="video-card">
          <a href="/watch?v=dQw4w9WgXcQ" title="Rick Astley Video">
            <img src="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg" alt="Rick Astley">
          </a>
        </div>
        <div class="video-card">
          <a href="/video/102938/quantum-physics">
            <img data-src="https://cdn.example.com/thumbs/102938.webp" alt="Quantum Physics">
            <span>Quantum Physics in 10 Min</span>
          </a>
        </div>
        <div class="video-card">
          <a href="/v/super-fast-car" title="Formula 1 Racing">
            <img data-original="https://cdn.example.com/thumbs/f1.jpg">
          </a>
        </div>
      </div>
    </body>
    </html>
    """

    def mock_fetch_homepage(request: httpx.Request):
        return httpx.Response(200, text=homepage_html, request=request)

    async def run_homepage_test():
        orig_async_client = httpx.AsyncClient
        try:
            httpx.AsyncClient = lambda **kwargs: orig_async_client(transport=httpx.MockTransport(mock_fetch_homepage), **kwargs)
            res = await VideoLinkFinder.find_links(
                url="https://videoshare.example.com/",
                routing_mode="direct",
                use_stealth=True
            )
            assert res["total_found"] == 3, f"Expected 3 video cards, got {res['total_found']}: {[l['title'] for l in res['links']]}"
            # Verify thumbnail and title
            first = res["links"][0]
            assert "hqdefault.jpg" in first["thumbnail"]
            assert first["format"] == "Video Card"
            assert first["type"] == "page_video"
        finally:
            httpx.AsyncClient = orig_async_client

    asyncio.run(run_homepage_test())

    # 8. Test Direct .mp4 Input URL
    async def run_direct_input_test():
        res = await VideoLinkFinder.find_links(
            url="https://cdn.example.com/storage/1/60/sample_direct_video.mp4",
            routing_mode="direct"
        )
        assert res["total_found"] >= 1
        assert res["links"][0]["url"] == "https://cdn.example.com/storage/1/60/sample_direct_video.mp4"
        assert res["links"][0]["format"] == "MP4"

    asyncio.run(run_direct_input_test())

    print("Video Link Finder (Stealth & Extraction) test: PASSED")

def test_bulk_delete_and_cancel_all():
    import tempfile
    from starlette.testclient import TestClient
    from app.main import app
    from app.database import db_create_video, db_get_video, db_delete_video

    desktop_client = TestClient(app, client=("127.0.0.1", 54321))
    phone_client = TestClient(app, client=("192.168.1.55", 54321))

    # 1. Create temporary files and records
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f1, \
         tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f2, \
         tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f3:
        p1, p2, p3 = f1.name, f2.name, f3.name
        f1.write(b"video1")
        f2.write(b"video2")
        f3.write(b"video3")

    id1, id2, id3 = "bulk_del_1", "bulk_del_2", "bulk_del_3"
    try:
        db_create_video({"id": id1, "url": "https://example.com/1.mp4", "title": "Video 1", "file_path": p1, "status": "completed"})
        db_create_video({"id": id2, "url": "https://example.com/2.mp4", "title": "Video 2", "file_path": p2, "status": "completed"})
        db_create_video({"id": id3, "url": "https://example.com/3.mp4", "title": "Video 3", "file_path": p3, "status": "completed"})

        # 2. Phone client is rejected with 403 Forbidden
        r_phone = phone_client.post("/api/videos/bulk-delete", json={"video_ids": [id1, id2]})
        assert r_phone.status_code == 403

        # 3. Desktop client successfully deletes multiple videos in bulk
        r_bulk = desktop_client.post("/api/videos/bulk-delete", json={"video_ids": [id1, id2]})
        assert r_bulk.status_code == 200
        res = r_bulk.json()
        assert res["success"] is True
        assert res["deleted_count"] == 2
        assert id1 in res["deleted_ids"] and id2 in res["deleted_ids"]

        # Ensure DB records and files are deleted
        assert db_get_video(id1) is None
        assert db_get_video(id2) is None
        assert not os.path.exists(p1)
        assert not os.path.exists(p2)

        # Ensure non-deleted video 3 remains
        assert db_get_video(id3) is not None
        assert os.path.exists(p3)

        # 4. Cancel all endpoint security and execution
        r_cancel_phone = phone_client.post("/api/downloads/cancel-all")
        assert r_cancel_phone.status_code == 403

        r_cancel_desk = desktop_client.post("/api/downloads/cancel-all")
        assert r_cancel_desk.status_code == 200
        assert r_cancel_desk.json()["success"] is True

        print("Bulk Delete & Cancel All API test: PASSED")
    finally:
        db_delete_video(id1)
        db_delete_video(id2)
        db_delete_video(id3)
        for p in (p1, p2, p3):
            if os.path.exists(p):
                os.unlink(p)

if __name__ == "__main__":
    test_db_operations()
    test_chunk_engine_merging()
    test_download_folder_configuration()
    test_video_stitching()
    test_media_tools()
    test_video_trimmer()
    test_batch_and_playlist_queuing()
    test_qr_and_mobile_stream()
    test_byte_range_mobile_seeking()
    test_stream_encryption_and_pin_security()
    test_single_direct_video_stream()
    test_desktop_security_boundaries()
    test_video_link_finder()
    test_bulk_delete_and_cancel_all()
    print("ALL TESTS PASSED SUCCESSFULLY!")
