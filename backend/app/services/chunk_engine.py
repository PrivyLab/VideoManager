import os
import asyncio
import httpx
import shutil
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Callable, Optional, Dict, Any
from app.config import CHUNKS_DIR, DEFAULT_VIDEOS_DIR, get_configured_download_dir

class ChunkEngine:
    """
    Engine for downloading video/audio streams in parallel byte chunks,
    sequential media segments, or single direct streams for hosts that
    do not support HTTP byte-ranges.
    """

    def __init__(self, video_id: str, client: Optional[httpx.AsyncClient] = None, referer: Optional[str] = None):
        self.video_id = video_id
        self.work_dir = CHUNKS_DIR / video_id
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.referer = referer
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def _get_headers(self, url: Optional[str] = None, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Construct standard desktop browser headers to prevent 403 blocks from CDNs."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if self.referer:
            headers["Referer"] = self.referer
        elif url:
            try:
                parsed = urlparse(url)
                if parsed.scheme and parsed.netloc:
                    headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
            except Exception:
                pass

        if custom_headers:
            headers.update(custom_headers)
        return headers

    async def probe_url(self, url: str) -> Dict[str, Any]:
        """Check if URL supports Range requests and get content length and content type."""
        headers = self._get_headers(url)
        try:
            resp = await self.client.head(url, headers=headers)
            if resp.status_code >= 400:
                # HEAD request failed or blocked (common on CDNs/imageboards); probe with streaming GET for initial headers
                async with self.client.stream("GET", url, headers={**headers, "Range": "bytes=0-0"}) as stream_resp:
                    content_length = int(stream_resp.headers.get("content-length", 0))
                    accept_ranges = "bytes" in stream_resp.headers.get("accept-ranges", "").lower() or stream_resp.status_code == 206
                    content_type = stream_resp.headers.get("content-type", "video/mp4")
                    content_range = stream_resp.headers.get("content-range")
                    if content_range and "/" in content_range:
                        total_from_range = content_range.split("/")[-1]
                        if total_from_range.isdigit():
                            content_length = int(total_from_range)
                            accept_ranges = True

                    return {
                        "content_length": content_length,
                        "accept_ranges": accept_ranges,
                        "content_type": content_type
                    }
            else:
                content_length = int(resp.headers.get("content-length", 0))
                accept_ranges = "bytes" in resp.headers.get("accept-ranges", "").lower() or resp.status_code == 206
                content_type = resp.headers.get("content-type", "video/mp4")
                
                content_range = resp.headers.get("content-range")
                if content_range and "/" in content_range:
                    total_from_range = content_range.split("/")[-1]
                    if total_from_range.isdigit():
                        content_length = int(total_from_range)
                        accept_ranges = True

                return {
                    "content_length": content_length,
                    "accept_ranges": accept_ranges,
                    "content_type": content_type
                }
        except Exception as e:
            return {
                "content_length": 0,
                "accept_ranges": False,
                "content_type": "video/mp4",
                "error": str(e)
            }

    async def download_direct_stream(
        self,
        url: str,
        output_filename: str,
        output_dir: Optional[Path] = None,
        total_size: int = 0,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Path:
        """
        Download a single direct video stream without chunks or range slicing.
        Ideal for single media files, servers without Range support, or unknown content-lengths.
        """
        dest_dir = output_dir or get_configured_download_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = dest_dir / output_filename
        part_path = self.work_dir / f"{output_filename}.part"

        headers = self._get_headers(url)

        if progress_callback:
            progress_callback({
                "progress": 0.0,
                "downloaded_bytes": 0,
                "total_bytes": total_size,
                "speed": "",
                "eta": "",
                "chunks_total": 1,
                "chunks_completed": 0,
                "status": "downloading",
                "message": "Connecting to direct video stream..."
            })

        downloaded = 0
        start_time = asyncio.get_event_loop().time()
        last_progress_time = start_time

        async with self.client.stream("GET", url, headers=headers) as response:
            if response.status_code >= 400:
                raise Exception(f"HTTP {response.status_code} fetching direct stream: {response.reason_phrase}")

            resp_len = response.headers.get("content-length")
            if resp_len and resp_len.isdigit() and int(resp_len) > 0:
                total_size = int(resp_len)

            with open(part_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if self._cancel_requested:
                        raise asyncio.CancelledError("Download cancelled by user")
                    f.write(chunk)
                    downloaded += len(chunk)

                    now = asyncio.get_event_loop().time()
                    if progress_callback and (now - last_progress_time >= 0.25 or (total_size > 0 and downloaded >= total_size)):
                        last_progress_time = now
                        elapsed = now - start_time
                        speed = (downloaded / elapsed) if elapsed > 0 else 0
                        speed_str = f"{speed / (1024 * 1024):.2f} MB/s" if speed > 1024 * 1024 else f"{speed / 1024:.1f} KB/s"
                        pct = min((downloaded / total_size * 100), 99.0) if total_size > 0 else 0.0
                        eta_str = f"{(total_size - downloaded) / speed:.1f}s" if (speed > 0 and total_size > 0 and total_size > downloaded) else ""
                        progress_callback({
                            "progress": pct,
                            "downloaded_bytes": downloaded,
                            "total_bytes": total_size,
                            "speed": speed_str,
                            "eta": eta_str,
                            "chunks_total": 1,
                            "chunks_completed": 1 if pct >= 99 else 0,
                            "status": "downloading"
                        })

        if self._cancel_requested:
            raise asyncio.CancelledError("Download cancelled by user")

        if part_path.exists():
            shutil.move(str(part_path), str(final_path))

        self.cleanup()

        if progress_callback:
            progress_callback({
                "progress": 100.0,
                "downloaded_bytes": downloaded,
                "total_bytes": downloaded,
                "speed": "",
                "eta": "0s",
                "chunks_total": 1,
                "chunks_completed": 1,
                "status": "completed",
                "message": "Direct single video download complete."
            })

        return final_path

    async def download_chunk_range(
        self,
        url: str,
        chunk_idx: int,
        start_byte: int,
        end_byte: Optional[int],
        chunk_path: Path,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Download a specific byte range to a chunk file."""
        if self._cancel_requested:
            return False

        range_val = f"bytes={start_byte}-{end_byte if end_byte is not None else ''}"
        headers = self._get_headers(url, {"Range": range_val})

        downloaded_in_chunk = 0
        expected_chunk_size = (end_byte - start_byte + 1) if end_byte is not None else None

        if chunk_path.exists() and expected_chunk_size is not None:
            existing_size = chunk_path.stat().st_size
            if existing_size == expected_chunk_size:
                if on_progress:
                    on_progress(chunk_idx, existing_size)
                return True
            else:
                chunk_path.unlink()

        async with self.client.stream("GET", url, headers=headers) as response:
            if response.status_code not in (200, 206):
                raise Exception(f"HTTP {response.status_code} fetching chunk {chunk_idx}")

            with open(chunk_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if self._cancel_requested:
                        return False
                    f.write(chunk)
                    downloaded_in_chunk += len(chunk)
                    if on_progress:
                        on_progress(chunk_idx, downloaded_in_chunk)

        return True

    async def download_with_chunking(
        self,
        url: str,
        output_filename: str,
        num_chunks: int = 4,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Path:
        """
        Splits file into `num_chunks` parts, downloads concurrently,
        and merges them into output_filename.
        If server doesn't support ranges or total_size is unknown or num_chunks == 1,
        delegates directly to download_direct_stream.
        """
        probe = await self.probe_url(url)
        total_size = probe.get("content_length", 0)
        accept_ranges = probe.get("accept_ranges", False)

        dest_dir = output_dir or get_configured_download_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = dest_dir / output_filename

        # If byte-ranges are not supported, total size unknown, or only 1 chunk requested:
        # Download directly as a single stream without chunk splitting and merging!
        if not accept_ranges or total_size <= 0 or num_chunks <= 1:
            return await self.download_direct_stream(
                url=url,
                output_filename=output_filename,
                output_dir=dest_dir,
                total_size=total_size,
                progress_callback=progress_callback
            )

        chunk_size = total_size // num_chunks
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_size
            end = total_size - 1 if i == num_chunks - 1 else (start + chunk_size - 1)
            chunks.append((start, end))

        chunk_files = [self.work_dir / f"chunk_{i}.part" for i in range(len(chunks))]
        chunk_progress = {i: 0 for i in range(len(chunks))}
        start_time = asyncio.get_event_loop().time()

        def update_progress(idx: int, bytes_done: int):
            chunk_progress[idx] = bytes_done
            total_done = sum(chunk_progress.values())
            pct = (total_done / total_size * 100) if total_size > 0 else 0
            elapsed = asyncio.get_event_loop().time() - start_time
            speed = (total_done / elapsed) if elapsed > 0 else 0
            speed_str = f"{speed / (1024 * 1024):.2f} MB/s" if speed > 1024 * 1024 else f"{speed / 1024:.1f} KB/s"
            completed_chunks = sum(1 for p in chunk_progress.values() if p > 0)

            if progress_callback:
                progress_callback({
                    "progress": min(pct, 99.0),
                    "downloaded_bytes": total_done,
                    "total_bytes": total_size,
                    "speed": speed_str,
                    "eta": f"{(total_size - total_done) / speed:.1f}s" if speed > 0 and total_size > 0 else "",
                    "chunks_total": len(chunks),
                    "chunks_completed": completed_chunks,
                    "status": "downloading"
                })

        tasks = []
        for i, (start, end) in enumerate(chunks):
            tasks.append(
                self.download_chunk_range(
                    url=url,
                    chunk_idx=i,
                    start_byte=start,
                    end_byte=end,
                    chunk_path=chunk_files[i],
                    on_progress=update_progress
                )
            )

        await asyncio.gather(*tasks)

        if self._cancel_requested:
            raise asyncio.CancelledError("Download cancelled by user")

        if progress_callback:
            progress_callback({
                "progress": 99.0,
                "status": "merging",
                "message": f"Merging {len(chunks)} chunks into final media file..."
            })

        merged_path = await self.merge_chunks(chunk_files, final_path)
        self.cleanup()

        if progress_callback:
            progress_callback({
                "progress": 100.0,
                "status": "completed",
                "chunks_total": len(chunks),
                "chunks_completed": len(chunks),
                "message": "File download and chunk assembly complete."
            })

        return merged_path

    async def download_segment_list(
        self,
        segment_urls: List[str],
        output_filename: str,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Path:
        """
        For websites that provide explicit chunks / segments.
        Downloads each segment and merges them in exact sequential order.
        """
        dest_dir = output_dir or get_configured_download_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = dest_dir / output_filename

        total_segments = len(segment_urls)
        chunk_files = []

        for idx, seg_url in enumerate(segment_urls):
            if self._cancel_requested:
                raise asyncio.CancelledError("Cancelled by user")

            chunk_file = self.work_dir / f"seg_{idx:05d}.part"
            chunk_files.append(chunk_file)

            async with self.client.stream("GET", seg_url) as resp:
                resp.raise_for_status()
                with open(chunk_file, "wb") as f:
                    async for b in resp.aiter_bytes(chunk_size=65536):
                        f.write(b)

            pct = ((idx + 1) / total_segments) * 99.0
            if progress_callback:
                progress_callback({
                    "progress": pct,
                    "chunks_total": total_segments,
                    "chunks_completed": idx + 1,
                    "status": "downloading",
                    "message": f"Downloaded chunk {idx + 1} of {total_segments}"
                })

        if progress_callback:
            progress_callback({
                "progress": 99.0,
                "status": "merging",
                "message": f"Merging {total_segments} media segments..."
            })

        merged_path = await self.merge_chunks(chunk_files, final_path)
        self.cleanup()

        if progress_callback:
            progress_callback({
                "progress": 100.0,
                "status": "completed",
                "chunks_total": total_segments,
                "chunks_completed": total_segments,
                "message": "Merged segments successfully."
            })

        return merged_path

    async def merge_chunks(self, chunk_paths: List[Path], output_path: Path) -> Path:
        """Sequential binary stream concatenation of chunks."""
        def _do_merge():
            with open(output_path, "wb") as out_f:
                for chunk_p in chunk_paths:
                    if not chunk_p.exists():
                        raise FileNotFoundError(f"Missing chunk file: {chunk_p}")
                    with open(chunk_p, "rb") as in_f:
                        while True:
                            buffer = in_f.read(1024 * 1024)
                            if not buffer:
                                break
                            out_f.write(buffer)
            return output_path

        return await asyncio.to_thread(_do_merge)

    def cleanup(self):
        """Remove temporary chunks directory for this task."""
        try:
            if self.work_dir.exists():
                for p in self.work_dir.iterdir():
                    if p.is_file():
                        p.unlink()
                self.work_dir.rmdir()
        except Exception:
            pass
