import os
import asyncio
import yt_dlp
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from app.config import DEFAULT_VIDEOS_DIR, get_configured_download_dir, get_active_tor_proxy, get_active_warp_proxy


def parse_time_seconds(val: Optional[str]) -> Optional[float]:
    """Converts a time string ('01:30', '01:15:30', or '90') into total seconds as a float."""
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    try:
        parts = val_str.split(":")
        if len(parts) == 1:
            return float(parts[0])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except Exception:
        return None
    return None

class YtDlpQuietLogger:
    """Suppresses stderr logging from yt-dlp when probing unsupported or custom URLs."""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class YtDlpDownloader:
    """Wrapper around yt-dlp Python API with real-time async callbacks."""

    def __init__(self, video_id: str):
        self.video_id = video_id
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    @staticmethod
    def build_proxy_string(
        use_tor: bool = False,
        custom_proxy: Optional[str] = None,
        routing_mode: Optional[str] = None
    ) -> Optional[str]:
        if custom_proxy and custom_proxy.strip():
            return custom_proxy.strip()
        if routing_mode == "warp":
            active_warp = get_active_warp_proxy()
            return active_warp or "socks5://127.0.0.1:1080"
        if routing_mode == "tor" or use_tor:
            active = get_active_tor_proxy()
            return active or "socks5://127.0.0.1:9150"
        return None

    @staticmethod
    def extract_info(
        url: str,
        referer: Optional[str] = None,
        use_tor: bool = False,
        custom_proxy: Optional[str] = None,
        routing_mode: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract metadata without downloading."""
        headers: Dict[str, str] = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if referer:
            headers['Referer'] = referer
            headers['Origin'] = '/'.join(referer.split('/')[:3])

        ydl_opts: Dict[str, Any] = {
            'extract_flat': False,
            'skip_download': True,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'logger': YtDlpQuietLogger(),
            'http_headers': headers,
        }

        proxy = YtDlpDownloader.build_proxy_string(use_tor, custom_proxy, routing_mode)
        if proxy:
            ydl_opts['proxy'] = proxy

        if cookies_from_browser and cookies_from_browser.strip():
            browser = cookies_from_browser.strip().lower()
            ydl_opts['cookiesfrombrowser'] = (browser,)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            if 'cookiesfrombrowser' in ydl_opts:
                # macOS permission (TCC) or browser cookie database not found:
                # Automatically retry anonymously without browser cookies!
                ydl_opts.pop('cookiesfrombrowser', None)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            else:
                raise e

        if not info:
            raise ValueError("Could not extract video metadata.")

            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    res = f.get('format_note') or (f"{f.get('height')}p" if f.get('height') else None)
                    ext = f.get('ext')
                    if res and ext:
                        formats.append({
                            "format_id": f.get('format_id'),
                            "ext": ext,
                            "resolution": res,
                            "filesize": f.get('filesize') or f.get('filesize_approx')
                        })

            return {
                "title": info.get("title", "Untitled Video"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail"),
                "description": (info.get("description") or "")[:200],
                "uploader": info.get("uploader", ""),
                "formats": formats,
            }

    @staticmethod
    def extract_playlist(
        url: str,
        referer: Optional[str] = None,
        use_tor: bool = False,
        custom_proxy: Optional[str] = None,
        routing_mode: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
        max_entries: int = 100
    ) -> Dict[str, Any]:
        """Extract playlist or channel metadata and entries without downloading."""
        headers: Dict[str, str] = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if referer:
            headers['Referer'] = referer
            headers['Origin'] = '/'.join(referer.split('/')[:3])

        ydl_opts: Dict[str, Any] = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'noplaylist': False,
            'quiet': True,
            'no_warnings': True,
            'logger': YtDlpQuietLogger(),
            'playlist_items': f"1-{max_entries}",
            'http_headers': headers,
        }

        proxy = YtDlpDownloader.build_proxy_string(use_tor, custom_proxy, routing_mode)
        if proxy:
            ydl_opts['proxy'] = proxy

        if cookies_from_browser and cookies_from_browser.strip():
            browser = cookies_from_browser.strip().lower()
            ydl_opts['cookiesfrombrowser'] = (browser,)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            if 'cookiesfrombrowser' in ydl_opts:
                ydl_opts.pop('cookiesfrombrowser', None)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            else:
                raise e

        if not info:
            raise ValueError("Could not extract playlist information.")

            is_playlist = info.get('_type') == 'playlist' or 'entries' in info
            raw_entries = info.get('entries') if is_playlist else [info]
            if raw_entries is None:
                raw_entries = [info]

            items = []
            for idx, entry in enumerate(raw_entries):
                if not entry:
                    continue
                entry_id = entry.get('id')
                entry_url = entry.get('url') or entry.get('webpage_url')
                if not entry_url and entry_id:
                    entry_url = f"https://www.youtube.com/watch?v={entry_id}"

                thumb = entry.get('thumbnail')
                if not thumb and entry.get('thumbnails'):
                    thumb = entry.get('thumbnails')[-1].get('url')

                items.append({
                    "index": idx + 1,
                    "id": entry_id or f"item_{idx + 1}",
                    "title": entry.get('title') or f"Video {idx + 1}",
                    "url": entry_url or url,
                    "duration": entry.get('duration') or 0,
                    "thumbnail": thumb or "",
                    "uploader": entry.get('uploader') or info.get('uploader') or "",
                })

            return {
                "is_playlist": is_playlist,
                "title": info.get('title') or "Playlist",
                "id": info.get('id') or "",
                "uploader": info.get('uploader') or "",
                "description": (info.get('description') or "")[:300],
                "total_count": len(items),
                "items": items
            }

    async def download(
        self,
        url: str,
        quality: str = "best",
        output_dir: Optional[Path] = None,
        referer: Optional[str] = None,
        use_tor: bool = False,
        custom_proxy: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
        routing_mode: Optional[str] = None,
        trim_start: Optional[str] = None,
        trim_end: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()

        dest_dir = output_dir or get_configured_download_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(dest_dir / f"{self.video_id}_%(title).100s.%(ext)s")

        format_selector = "bestvideo+bestaudio/best"
        if quality == "1080p":
            format_selector = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        elif quality == "720p":
            format_selector = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif quality == "480p":
            format_selector = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        elif quality == "audio":
            format_selector = "bestaudio/best"

        final_file_info: Dict[str, Any] = {
            "file_path": None, "title": "", "duration": 0, "resolution": "", "thumbnail": ""
        }

        # Build HTTP headers
        headers: Dict[str, str] = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        if referer:
            headers['Referer'] = referer
            headers['Origin'] = '/'.join(referer.split('/')[:3])

        def hook(d: Dict[str, Any]):
            if self._cancel_requested:
                raise Exception("Download cancelled by user")
            status = d.get('status')
            if status == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0
                pct = (downloaded / total * 100) if total > 0 else 0
                speed_str = (
                    f"{speed / (1024*1024):.2f} MB/s" if speed > 1024*1024
                    else f"{speed / 1024:.1f} KB/s"
                )
                if progress_callback:
                    progress_callback({
                        "status": "downloading",
                        "progress": round(pct, 1),
                        "speed": speed_str,
                        "eta": f"{int(eta)}s" if eta else "",
                        "downloaded_bytes": downloaded,
                        "total_bytes": total,
                    })
            elif status == 'finished':
                filename = d.get('filename')
                if filename:
                    final_file_info["file_path"] = filename
                if progress_callback:
                    progress_callback({
                        "status": "merging",
                        "progress": 99.0,
                        "message": "Finishing and merging media streams...",
                    })

        ydl_opts: Dict[str, Any] = {
            'format': format_selector,
            'outtmpl': out_template,
            'merge_output_format': 'mp4',
            'postprocessor_args': {
                'Merger': ['-movflags', '+faststart'],
            },
            'progress_hooks': [hook],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'concurrent_fragment_downloads': 5,
            'fragment_retries': 10,
            'retries': 10,
            'http_headers': headers,
        }

        # Proxy (Tor, Cloudflare WARP, or custom)
        proxy = self.build_proxy_string(use_tor, custom_proxy, routing_mode)
        if proxy:
            ydl_opts['proxy'] = proxy

        # Cookies from installed browser
        if cookies_from_browser and cookies_from_browser.strip():
            browser = cookies_from_browser.strip().lower()
            ydl_opts['cookiesfrombrowser'] = (browser,)

        # Pre-download range/trim support
        start_sec = parse_time_seconds(trim_start)
        end_sec = parse_time_seconds(trim_end)
        if start_sec is not None or end_sec is not None:
            s = start_sec if start_sec is not None else 0.0
            e = end_sec if end_sec is not None else float("inf")
            try:
                from yt_dlp.utils import download_range_func
                ydl_opts['download_ranges'] = download_range_func(None, [(s, e)])
                ydl_opts['force_keyframes_at_cuts'] = True
            except Exception:
                pass

        def _run_ydl():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception as e:
                if 'cookiesfrombrowser' in ydl_opts:
                    ydl_opts.pop('cookiesfrombrowser', None)
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                else:
                    raise e

            actual_filename = ydl.prepare_filename(info)
            if not Path(actual_filename).exists():
                stem = Path(actual_filename).stem
                matches = list(dest_dir.glob(f"{stem}.*"))
                if matches:
                    actual_filename = str(matches[0])
            final_file_info["file_path"] = actual_filename
            final_file_info["title"] = info.get("title", "Untitled")
            final_file_info["duration"] = info.get("duration", 0)
            final_file_info["thumbnail"] = info.get("thumbnail", "")
            final_file_info["resolution"] = f"{info.get('width', '')}x{info.get('height', '')}"
            return final_file_info

        return await loop.run_in_executor(None, _run_ydl)
