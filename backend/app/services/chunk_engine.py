import os
import asyncio
import httpx
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
from app.config import CHUNKS_DIR, DEFAULT_VIDEOS_DIR, get_configured_download_dir

class ChunkEngine:
    """
    Engine for downloading video/audio streams in parallel byte chunks
    or sequential media segments, and assembling/merging them cleanly into
    the final media file.
    """

    def __init__(self, video_id: str, client: Optional[httpx.AsyncClient] = None):
        self.video_id = video_id
        self.work_dir = CHUNKS_DIR / video_id
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.client = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    async def probe_url(self, url: str) -> Dict[str, Any]:
        """Check if URL supports Range requests and get content length and content type."""
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) VideoManager/1.0"}
        try:
            resp = await self.client.head(url, headers=headers)
            if resp.status_code >= 400:
                headers["Range"] = "bytes=0-0"
                resp = await self.client.get(url, headers=headers)

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

    async def download_chunk_range(
        self,
        url: str,
        chunk_idx: int,
        start_byte: int,
        end_byte: int,
        chunk_path: Path,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Download a specific byte range to a chunk file."""
        if self._cancel_requested:
            return False

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) VideoManager/1.0",
            "Range": f"bytes={start_byte}-{end_byte}"
        }

        downloaded_in_chunk = 0
        expected_chunk_size = end_byte - start_byte + 1

        if chunk_path.exists():
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
        """
        probe = await self.probe_url(url)
        total_size = probe.get("content_length", 0)
        accept_ranges = probe.get("accept_ranges", False)

        dest_dir = output_dir or get_configured_download_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = dest_dir / output_filename

        if not accept_ranges or total_size <= 0:
            num_chunks = 1
            chunks = [(0, total_size - 1 if total_size > 0 else None)]
        else:
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
