import asyncio
import uuid
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Set
from fastapi import WebSocket

from app.database import db_create_video, db_update_video, db_get_video, db_get_all_videos
from app.config import get_configured_download_dir, cleanup_video_artifacts
from app.models import DownloadRequest
from app.services.chunk_engine import ChunkEngine
from app.services.ytdlp_downloader import YtDlpDownloader
from app.services.video_stitcher import VideoStitcher

class DownloadManager:
    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.active_downloaders: Dict[str, Any] = {}
        self.websockets: Set[WebSocket] = set()

    async def register_ws(self, ws: WebSocket):
        self.websockets.add(ws)

    def unregister_ws(self, ws: WebSocket):
        self.websockets.discard(ws)

    async def broadcast(self, data: Dict[str, Any]):
        """Send update to all active WebSocket clients."""
        dead_sockets = set()
        for ws in self.websockets:
            try:
                await ws.send_json(data)
            except Exception:
                dead_sockets.add(ws)
        self.websockets.difference_update(dead_sockets)

    async def start_download(self, req: DownloadRequest) -> str:
        video_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        initial_record = {
            "id": video_id,
            "url": req.url,
            "title": req.custom_title or "Fetching video info...",
            "duration": 0,
            "file_path": "",
            "file_size": 0,
            "file_format": "",
            "thumbnail_url": "",
            "resolution": "",
            "status": "queued",
            "progress": 0.0,
            "speed": "",
            "eta": "",
            "error_message": "",
            "downloader_type": req.downloader_type or "auto",
            "chunks_total": req.custom_chunks if req.downloader_type == "chunked" else 0,
            "chunks_completed": 0,
            "created_at": now,
            "completed_at": None
        }
        db_create_video(initial_record)

        await self.broadcast({
            "event": "video_created",
            "video": initial_record
        })

        task = asyncio.create_task(self._run_download_task(video_id, req))
        self.active_tasks[video_id] = task
        return video_id

    async def cancel_download(self, video_id: str) -> bool:
        if video_id in self.active_downloaders:
            self.active_downloaders[video_id].cancel()
        if video_id in self.active_tasks:
            self.active_tasks[video_id].cancel()
            self.active_tasks.pop(video_id, None)

        cleanup_video_artifacts(video_id, keep_final=False)

        db_update_video(video_id, {
            "status": "cancelled",
            "error_message": "Download cancelled by user"
        })

        await self.broadcast({
            "event": "progress",
            "video_id": video_id,
            "status": "cancelled",
            "progress": 0,
            "message": "Download cancelled"
        })
        return True

    async def _run_download_task(self, video_id: str, req: DownloadRequest):
        main_loop = asyncio.get_running_loop()

        db_update_video(video_id, {"status": "downloading"})
        await self.broadcast({
            "event": "progress",
            "video_id": video_id,
            "status": "downloading",
            "progress": 0.0
        })

        def progress_cb(info: Dict[str, Any]):
            status = info.get("status", "downloading")
            progress = info.get("progress", 0.0)
            speed = info.get("speed", "")
            eta = info.get("eta", "")
            msg = info.get("message", "")
            chunks_total = info.get("chunks_total", 0)
            chunks_completed = info.get("chunks_completed", 0)

            db_update_video(video_id, {
                "status": status,
                "progress": progress,
                "speed": speed,
                "eta": eta,
                "chunks_total": chunks_total,
                "chunks_completed": chunks_completed
            })

            # Safely schedule the broadcast on the main event loop from thread
            coro = self.broadcast({
                "event": "progress",
                "video_id": video_id,
                "status": status,
                "progress": progress,
                "speed": speed,
                "eta": eta,
                "message": msg,
                "chunks_total": chunks_total,
                "chunks_completed": chunks_completed
            })
            asyncio.run_coroutine_threadsafe(coro, main_loop)

        try:
            target_folder = None
            if req.download_folder and req.download_folder.strip():
                target_folder = Path(req.download_folder.strip()).expanduser().resolve()
            else:
                target_folder = get_configured_download_dir()
            target_folder.mkdir(parents=True, exist_ok=True)

            use_chunk_engine = False
            if req.downloader_type == "chunked" or (req.chunk_urls and len(req.chunk_urls) > 0):
                use_chunk_engine = True
            elif req.downloader_type == "auto":
                if any(req.url.lower().split("?")[0].endswith(ext) for ext in [".mp4", ".mkv", ".webm", ".mov", ".ts"]):
                    use_chunk_engine = True

            if use_chunk_engine:
                engine = ChunkEngine(video_id)
                self.active_downloaders[video_id] = engine

                filename = f"{video_id}_video.mp4"
                if req.chunk_urls:
                    final_path = await engine.download_segment_list(
                        req.chunk_urls,
                        output_filename=filename,
                        output_dir=target_folder,
                        progress_callback=progress_cb
                    )
                else:
                    final_path = await engine.download_with_chunking(
                        req.url,
                        output_filename=filename,
                        num_chunks=req.custom_chunks or 4,
                        output_dir=target_folder,
                        progress_callback=progress_cb
                    )

                file_size = final_path.stat().st_size if final_path.exists() else 0
                now = datetime.utcnow().isoformat()
                updates = {
                    "title": req.custom_title or final_path.name,
                    "file_path": str(final_path),
                    "file_size": file_size,
                    "file_format": final_path.suffix.replace(".", ""),
                    "status": "completed",
                    "progress": 100.0,
                    "speed": "",
                    "eta": "",
                    "downloader_type": "chunked",
                    "completed_at": now
                }
                cleanup_video_artifacts(video_id, file_path=str(final_path), keep_final=True)
                db_update_video(video_id, updates)
                await self.broadcast({
                    "event": "completed",
                    "video_id": video_id,
                    "video": db_get_video(video_id)
                })

            else:
                downloader = YtDlpDownloader(video_id)
                self.active_downloaders[video_id] = downloader

                res = await downloader.download(
                    url=req.url,
                    quality=req.quality or "best",
                    output_dir=target_folder,
                    referer=req.referer,
                    use_tor=req.use_tor or False,
                    custom_proxy=req.custom_proxy,
                    cookies_from_browser=req.cookies_from_browser,
                    routing_mode=req.routing_mode,
                    progress_callback=progress_cb,
                )

                file_path = res.get("file_path")
                file_size = 0
                file_format = "mp4"
                if file_path and Path(file_path).exists():
                    p = Path(file_path)
                    file_size = p.stat().st_size
                    file_format = p.suffix.replace(".", "")

                now = datetime.utcnow().isoformat()
                updates = {
                    "title": res.get("title") or req.custom_title or "Downloaded Video",
                    "duration": res.get("duration", 0),
                    "file_path": file_path or "",
                    "file_size": file_size,
                    "file_format": file_format,
                    "thumbnail_url": res.get("thumbnail") or "",
                    "resolution": res.get("resolution") or "",
                    "status": "completed",
                    "progress": 100.0,
                    "speed": "",
                    "eta": "",
                    "downloader_type": "ytdlp",
                    "completed_at": now
                }
                cleanup_video_artifacts(video_id, file_path=file_path, keep_final=True)
                db_update_video(video_id, updates)
                await self.broadcast({
                    "event": "completed",
                    "video_id": video_id,
                    "video": db_get_video(video_id)
                })

        except asyncio.CancelledError:
            cleanup_video_artifacts(video_id, keep_final=False)
            db_update_video(video_id, {"status": "cancelled", "error_message": "Cancelled"})
            await self.broadcast({
                "event": "progress",
                "video_id": video_id,
                "status": "cancelled",
                "message": "Download was cancelled."
            })
        except Exception as e:
            cleanup_video_artifacts(video_id, keep_final=False)
            err = str(e)
            db_update_video(video_id, {"status": "failed", "error_message": err})
            await self.broadcast({
                "event": "failed",
                "video_id": video_id,
                "status": "failed",
                "error": err
            })
        finally:
            self.active_tasks.pop(video_id, None)
            self.active_downloaders.pop(video_id, None)

    async def start_stitch(self, video_ids: list, title: Optional[str] = None, mode: str = "auto") -> str:
        job_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        # Validate input videos
        valid_videos = []
        for vid in video_ids:
            v = db_get_video(vid)
            if v and v.get("file_path") and Path(v["file_path"]).exists():
                valid_videos.append(v)

        if len(valid_videos) < 2:
            raise ValueError(f"Need at least 2 valid completed videos to stitch, found {len(valid_videos)}.")

        total_est_duration = sum(v.get("duration", 0) or 0 for v in valid_videos)
        default_title = f"Stitched Video ({len(valid_videos)} clips)"
        actual_title = title.strip() if title and title.strip() else default_title

        initial_record = {
            "id": job_id,
            "url": f"stitched://{','.join(video_ids)}",
            "title": actual_title,
            "duration": total_est_duration,
            "file_path": "",
            "file_size": 0,
            "file_format": "mp4",
            "thumbnail_url": "",
            "resolution": "",
            "status": "merging",
            "progress": 10.0,
            "speed": "",
            "eta": "",
            "error_message": "",
            "downloader_type": "stitch",
            "chunks_total": len(valid_videos),
            "chunks_completed": 0,
            "created_at": now,
            "completed_at": None,
        }
        db_create_video(initial_record)

        await self.broadcast({
            "event": "video_created",
            "video": initial_record
        })

        task = asyncio.create_task(self._run_stitch_task(job_id, valid_videos, actual_title, mode))
        self.active_tasks[job_id] = task
        return job_id

    async def _run_stitch_task(self, job_id: str, valid_videos: list, title: str, mode: str):
        main_loop = asyncio.get_running_loop()
        stitcher = VideoStitcher(job_id)
        self.active_downloaders[job_id] = stitcher

        def progress_cb(info: Dict[str, Any]):
            status = info.get("status", "merging")
            progress = info.get("progress", 50.0)
            msg = info.get("message", "")

            db_update_video(job_id, {
                "status": status,
                "progress": progress,
            })

            coro = self.broadcast({
                "event": "progress",
                "video_id": job_id,
                "status": status,
                "progress": progress,
                "message": msg,
                "chunks_total": len(valid_videos),
                "chunks_completed": int(len(valid_videos) * (progress / 100.0)),
            })
            asyncio.run_coroutine_threadsafe(coro, main_loop)

        try:
            target_folder = get_configured_download_dir()
            input_paths = [Path(v["file_path"]) for v in valid_videos]
            filename = f"{job_id}_{title.replace(' ', '_').replace('/', '_')}.mp4"

            res = await stitcher.stitch(
                input_paths=input_paths,
                output_dir=target_folder,
                output_filename=filename,
                mode=mode,
                progress_cb=progress_cb
            )

            now = datetime.utcnow().isoformat()
            updates = {
                "title": title,
                "duration": res.get("duration", 0),
                "file_path": res.get("file_path", ""),
                "file_size": res.get("file_size", 0),
                "file_format": "mp4",
                "thumbnail_url": res.get("thumbnail_url", ""),
                "resolution": res.get("resolution", ""),
                "status": "completed",
                "progress": 100.0,
                "speed": "",
                "eta": "",
                "downloader_type": "stitch",
                "completed_at": now
            }
            db_update_video(job_id, updates)
            await self.broadcast({
                "event": "completed",
                "video_id": job_id,
                "video": db_get_video(job_id)
            })

        except asyncio.CancelledError:
            db_update_video(job_id, {"status": "cancelled", "error_message": "Stitching cancelled"})
            await self.broadcast({
                "event": "progress",
                "video_id": job_id,
                "status": "cancelled",
                "message": "Stitching cancelled."
            })
        except Exception as e:
            err = str(e)
            db_update_video(job_id, {"status": "failed", "error_message": err})
            await self.broadcast({
                "event": "failed",
                "video_id": job_id,
                "status": "failed",
                "error": err
            })
        finally:
            self.active_tasks.pop(job_id, None)
            self.active_downloaders.pop(job_id, None)

download_manager = DownloadManager()
