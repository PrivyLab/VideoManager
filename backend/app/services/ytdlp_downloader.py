import os
import asyncio
import yt_dlp
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from app.config import DEFAULT_VIDEOS_DIR, get_configured_download_dir

TOR_PROXY = "socks5://127.0.0.1:9050"

class YtDlpDownloader:
    """Wrapper around yt-dlp Python API with real-time async callbacks."""

    def __init__(self, video_id: str):
        self.video_id = video_id
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    @staticmethod
    def build_proxy_string(use_tor: bool = False, custom_proxy: Optional[str] = None) -> Optional[str]:
        if custom_proxy and custom_proxy.strip():
            return custom_proxy.strip()
        if use_tor:
            return TOR_PROXY
        return None

    @staticmethod
    def extract_info(
        url: str,
        referer: Optional[str] = None,
        use_tor: bool = False,
        custom_proxy: Optional[str] = None,
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
            'http_headers': headers,
        }

        proxy = YtDlpDownloader.build_proxy_string(use_tor, custom_proxy)
        if proxy:
            ydl_opts['proxy'] = proxy

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
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

    async def download(
        self,
        url: str,
        quality: str = "best",
        output_dir: Optional[Path] = None,
        referer: Optional[str] = None,
        use_tor: bool = False,
        custom_proxy: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
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
            'progress_hooks': [hook],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'concurrent_fragment_downloads': 5,
            'fragment_retries': 10,
            'retries': 10,
            'http_headers': headers,
        }

        # Proxy (Tor or custom)
        proxy = self.build_proxy_string(use_tor, custom_proxy)
        if proxy:
            ydl_opts['proxy'] = proxy

        # Cookies from installed browser
        if cookies_from_browser and cookies_from_browser.strip():
            browser = cookies_from_browser.strip().lower()
            ydl_opts['cookiesfrombrowser'] = (browser,)

        def _run_ydl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
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
