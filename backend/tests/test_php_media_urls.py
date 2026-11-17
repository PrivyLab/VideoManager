import asyncio

import httpx
import pytest

from app.routers import downloads
from app.models import InspectRequest
from app.services import chunk_engine
from app.services.chunk_engine import (
    ChunkEngine,
    media_extension_from_url,
    query_video_extension_from_url,
)
from app.services.download_manager import extract_filename_from_url


def test_php_endpoint_with_media_query_is_detected_without_using_token_as_filename():
    url = (
        "https://media.example/remote_control.php"
        "?file=opaque-token.mp4&acctoken=secret-token"
    )

    assert media_extension_from_url(url) == ".mp4"
    assert query_video_extension_from_url(url) == ".mp4"
    assert query_video_extension_from_url("https://media.example/audio.mp3") is None
    filename = extract_filename_from_url(url)
    assert filename.endswith(".mp4")
    assert "opaque-token" not in filename
    assert "secret-token" not in filename
    assert extract_filename_from_url("https://media.example/video.mp4") == "video.mp4"


def test_inspect_php_media_endpoint_uses_direct_stream_probe(monkeypatch):
    class FakeChunkEngine:
        def __init__(self, _video_id):
            pass

        async def probe_url(self, _url):
            return {"content_type": "video/mp4", "content_length": 1234}

        def cleanup(self):
            pass

    monkeypatch.setattr(downloads, "ChunkEngine", FakeChunkEngine)
    monkeypatch.setattr(
        downloads.YtDlpDownloader,
        "extract_info",
        lambda _url: pytest.fail("yt-dlp should not inspect a direct PHP media endpoint"),
    )

    result = asyncio.run(
        downloads.inspect_url(
            InspectRequest(
                url=(
                    "https://media.example/remote_control.php"
                    "?file=opaque-token.mp4&acctoken=secret-token"
                )
            )
        )
    )

    assert result["source"] == "direct"
    assert result["info"]["formats"][0]["ext"] == "mp4"


def test_direct_stream_rejects_html_response(monkeypatch, tmp_path):
    async def run_test():
        transport = httpx.MockTransport(
            lambda _request: httpx.Response(200, headers={"content-type": "text/html"}, text="login")
        )
        client = httpx.AsyncClient(transport=transport)
        monkeypatch.setattr(chunk_engine, "CHUNKS_DIR", tmp_path / "chunks")
        engine = ChunkEngine("php-media", client=client)
        try:
            with pytest.raises(ValueError, match="not a recognized media stream"):
                await engine.download_direct_stream(
                    "https://media.example/remote_control.php?file=video.mp4",
                    "video.mp4",
                    output_dir=tmp_path / "downloads",
                    validate_media_response=True,
                )
            assert not (tmp_path / "downloads" / "video.mp4").exists()
        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_direct_stream_accepts_video_response_for_php_endpoint(monkeypatch, tmp_path):
    async def run_test():
        transport = httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                headers={"content-type": "video/mp4"},
                content=b"video-data",
            )
        )
        client = httpx.AsyncClient(transport=transport)
        monkeypatch.setattr(chunk_engine, "CHUNKS_DIR", tmp_path / "chunks")
        engine = ChunkEngine("php-media-ok", client=client)
        try:
            path = await engine.download_direct_stream(
                "https://media.example/remote_control.php?file=video.mp4",
                "video.mp4",
                output_dir=tmp_path / "downloads",
                validate_media_response=True,
            )
            assert path.read_bytes() == b"video-data"
        finally:
            await client.aclose()

    asyncio.run(run_test())
