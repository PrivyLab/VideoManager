import re
import json
import asyncio
import httpx
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, unquote
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

from app.config import get_active_tor_proxy, get_active_warp_proxy
from app.services.ytdlp_downloader import YtDlpDownloader

STEALTH_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

MEDIA_EXTENSIONS = (
    ".mp4", ".webm", ".mkv", ".mov", ".ts", ".m3u8", ".mpd",
    ".m4v", ".flv", ".avi", ".3gp", ".wmv"
)

STATIC_ASSET_EXTENSIONS = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".avif", ".ico", ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z", ".map"
)

VIDEO_WATCH_PATTERNS = [
    r'/(?:watch|video|videos|v|clip|clips|post|posts|item|media|view|play|embed|archive)/',
    r'/(?:watch|video|videos|v|clip|clips|post|posts|item|media|view|play|embed|archive)\b',
    r'[?&](?:v|viewkey|video_id|vid|clip_id)=',
    r'youtu\.be/',
    r'/shorts/',
    r'/reel/',
    r'/status/\d+',
]

IGNORE_NAV_ROUTES = (
    "/login", "/register", "/signup", "/terms", "/privacy",
    "/about", "/contact", "/dmca", "/faq", "/settings",
    "/account", "/rules", "/feedback", "/help"
)


class MediaHTMLParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.title = ""
        self.in_title = False
        self.og_title = ""
        self.og_image = ""
        self.video_poster = ""
        self.media_items: List[Dict[str, Any]] = []
        self._in_script = False
        self._script_buffer: List[str] = []
        self._current_a: Optional[Dict[str, Any]] = None
        self._last_img: Optional[Tuple[str, str]] = None
        self.discovered_thumbnails: List[str] = []

    @staticmethod
    def is_media_url(url: str) -> bool:
        """Determines if a URL points to a direct video or audio stream file."""
        if not url:
            return False
        clean = url.lower().split("?")[0].split("#")[0].strip()
        return clean.endswith(MEDIA_EXTENSIONS)

    @staticmethod
    def is_video_watch_url(href: str) -> bool:
        """Detects whether an anchor points to a video watch page on video sites / homepages."""
        if not href:
            return False
        p = href.lower().strip()
        clean = p.split("?")[0].split("#")[0]
        if any(clean.endswith(ext) for ext in STATIC_ASSET_EXTENSIONS):
            return False
        if any(nav in clean for nav in IGNORE_NAV_ROUTES):
            return False
        return any(re.search(pat, p) for pat in VIDEO_WATCH_PATTERNS)

    @staticmethod
    def _extract_img_src(attr_dict: Dict[str, str]) -> str:
        for attr in ("src", "data-src", "data-original", "data-thumb", "data-thumbnail", "data-lazy-src", "data-poster"):
            val = attr_dict.get(attr)
            if val and val.strip():
                return val.strip()
        return ""

    @staticmethod
    def _extract_media_attr(attr_dict: Dict[str, str]) -> Optional[str]:
        for attr in (
            "data-src", "data-video", "data-url", "data-href",
            "data-file", "data-mp4", "data-stream", "data-download",
            "data-orig", "data-original-url", "data-media"
        ):
            val = attr_dict.get(attr)
            if val and val.strip():
                clean = val.lower().split("?")[0].split("#")[0].strip()
                if clean.endswith(MEDIA_EXTENSIONS):
                    return val.strip()
        return None

    def handle_starttag(self, tag: str, attrs: list):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()

        if tag_lower == "title":
            self.in_title = True
        elif tag_lower == "script":
            self._in_script = True
            self._script_buffer = []
        elif tag_lower == "meta":
            prop = attr_dict.get("property", "").lower()
            name = attr_dict.get("name", "").lower()
            content = attr_dict.get("content", "").strip()

            if prop in ("og:title", "twitter:title"):
                self.og_title = content
            elif prop in ("og:image", "twitter:image") and content:
                self.og_image = urljoin(self.base_url, content)
                self.discovered_thumbnails.append(self.og_image)
            elif prop in ("og:video", "og:video:url", "og:video:secure_url") and content:
                full_url = urljoin(self.base_url, content)
                self.media_items.append({
                    "url": full_url,
                    "source": "OpenGraph Video Meta",
                    "type": self._classify_type(full_url),
                    "thumbnail": self.og_image or ""
                })
            elif name in ("twitter:player:stream", "twitter:player") and content:
                full_url = urljoin(self.base_url, content)
                self.media_items.append({
                    "url": full_url,
                    "source": "Twitter Player Card",
                    "type": self._classify_type(full_url),
                    "thumbnail": self.og_image or ""
                })

        elif tag_lower == "img":
            img_src = self._extract_img_src(attr_dict)
            alt = attr_dict.get("alt") or attr_dict.get("title") or ""
            if img_src:
                full_img = urljoin(self.base_url, img_src)
                self._last_img = (full_img, alt.strip())
                self.discovered_thumbnails.append(full_img)
                if self._current_a:
                    if not self._current_a["thumbnail"]:
                        self._current_a["thumbnail"] = full_img
                    if not self._current_a["title"] and alt.strip():
                        self._current_a["title"] = alt.strip()

        elif tag_lower == "video":
            src = attr_dict.get("src") or self._extract_media_attr(attr_dict)
            poster = attr_dict.get("poster")
            if poster:
                self.video_poster = urljoin(self.base_url, poster)
                self.discovered_thumbnails.append(self.video_poster)
            if src:
                full_url = urljoin(self.base_url, src)
                self.media_items.append({
                    "url": full_url,
                    "source": "HTML5 <video>",
                    "type": self._classify_type(full_url),
                    "thumbnail": self.video_poster or self.og_image or ""
                })

        elif tag_lower == "source":
            src = attr_dict.get("src") or attr_dict.get("data-src")
            mime = attr_dict.get("type", "")
            if src:
                full_url = urljoin(self.base_url, src)
                self.media_items.append({
                    "url": full_url,
                    "source": f"HTML5 <source> ({mime})" if mime else "HTML5 <source>",
                    "type": self._classify_type(full_url, mime),
                    "thumbnail": self.video_poster or self.og_image or ""
                })

        elif tag_lower == "iframe":
            src = attr_dict.get("src") or attr_dict.get("data-src")
            if src:
                full_url = urljoin(self.base_url, src)
                if any(p in full_url.lower() for p in [
                    "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
                    "bilibili.com", "streamtape", "streamwish", "voe.sx", "player.",
                    "embed", "rumble.com", "odysee.com"
                ]):
                    self.media_items.append({
                        "url": full_url,
                        "source": "Embedded Player (iframe)",
                        "type": "embedded_player",
                        "thumbnail": self.og_image or ""
                    })

        elif tag_lower == "a":
            href = attr_dict.get("href") or attr_dict.get("data-href") or attr_dict.get("data-src") or ""
            href = href.strip()
            title = attr_dict.get("title") or attr_dict.get("aria-label") or ""
            self._current_a = {
                "href": href,
                "title": title.strip(),
                "thumbnail": "",
                "text": []
            }

        else:
            # Check arbitrary tag for media attributes (e.g. <div data-video="..."> or <button data-src="...">)
            media_src = self._extract_media_attr(attr_dict)
            if media_src:
                full_url = urljoin(self.base_url, media_src)
                thumb_src = self._extract_img_src(attr_dict)
                thumb = urljoin(self.base_url, thumb_src) if thumb_src else (self.og_image or self.video_poster or "")
                self.media_items.append({
                    "url": full_url,
                    "source": f"HTML Tag Media Attribute (<{tag_lower}>)",
                    "type": self._classify_type(full_url),
                    "thumbnail": thumb,
                    "title": attr_dict.get("title") or attr_dict.get("aria-label") or ""
                })

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower == "title":
            self.in_title = False
        elif tag_lower == "script":
            self._in_script = False
            script_text = "".join(self._script_buffer)
            self._inspect_script_text(script_text)
        elif tag_lower == "a" and self._current_a:
            href = self._current_a["href"]
            if href:
                full_url = urljoin(self.base_url, href)
                raw_text = " ".join(self._current_a["text"]).strip()
                title = self._current_a["title"] or raw_text
                thumb = self._current_a["thumbnail"]

                # If no thumbnail inside <a>, check if preceded directly by an image
                if not thumb and self._last_img:
                    thumb = self._last_img[0]
                    if not title and self._last_img[1]:
                        title = self._last_img[1]

                if self.is_media_url(href):
                    self.media_items.append({
                        "url": full_url,
                        "title": title,
                        "source": "Page Media Link (<a>)",
                        "type": self._classify_type(full_url),
                        "thumbnail": thumb or self.og_image or ""
                    })
                elif self.is_video_watch_url(href):
                    self.media_items.append({
                        "url": full_url,
                        "title": title,
                        "source": "Homepage Video Card",
                        "type": "page_video",
                        "thumbnail": thumb or self.og_image or ""
                    })
            self._current_a = None

    def handle_data(self, data: str):
        if self.in_title and not self.title:
            self.title = data.strip()
        elif self._in_script:
            self._script_buffer.append(data)
        elif self._current_a:
            text = data.strip()
            if text:
                self._current_a["text"].append(text)

    def _inspect_script_text(self, text: str):
        """Scans inline script configurations (JWPlayer, Video.js, JSON-LD) for stream URLs."""
        if not text or len(text) < 10:
            return

        unescaped = text.replace(r"\/", "/").replace(r"\u0026", "&")

        # 1. JSON-LD VideoObject
        if "VideoObject" in unescaped:
            try:
                # Find all JSON blocks in script
                for json_candidate in re.findall(r'\{[^{}]*"@type"\s*:\s*"VideoObject"[^{}]*\}', unescaped):
                    try:
                        item = json.loads(json_candidate)
                        c_url = item.get("contentUrl") or item.get("embedUrl")
                        if c_url:
                            self.media_items.append({
                                "url": urljoin(self.base_url, c_url),
                                "source": "Schema.org VideoObject (JSON-LD)",
                                "type": self._classify_type(c_url),
                                "title": item.get("name") or "",
                                "thumbnail": item.get("thumbnailUrl") or ""
                            })
                    except Exception:
                        pass
            except Exception:
                pass

        # 2. HLS .m3u8 or DASH .mpd URLs inside scripts
        for m3u8_match in re.findall(r'(?:https?:)?//[^\s"\'<>]+\.m3u8(?:[?][^\s"\'<>]*)?', unescaped, re.I):
            self.media_items.append({
                "url": urljoin(self.base_url, m3u8_match),
                "source": "HLS Stream Manifest (.m3u8)",
                "type": "hls_stream"
            })

        for mpd_match in re.findall(r'(?:https?:)?//[^\s"\'<>]+\.mpd(?:[?][^\s"\'<>]*)?', unescaped, re.I):
            self.media_items.append({
                "url": urljoin(self.base_url, mpd_match),
                "source": "DASH Stream Manifest (.mpd)",
                "type": "dash_stream"
            })

        # 3. Direct video URLs in JS player configs
        js_video_patterns = [
            r'(?:file|source|videoUrl|playbackUrl|src|contentUrl)\s*:\s*["\']((?:https?:)?//[^\s"\'<>]+\.(?:mp4|webm|mkv|mov)[^\s"\'<>]*)["\']',
            r'(?:file|source|videoUrl|playbackUrl|src|contentUrl)\s*=\s*["\']((?:https?:)?//[^\s"\'<>]+\.(?:mp4|webm|mkv|mov)[^\s"\'<>]*)["\']',
            r'["\']((?:https?:)?//[^\s"\'<>]+\.(?:mp4|webm|mkv|mov)(?:\?[^\s"\'<>]*)?)["\']',
        ]
        for pat in js_video_patterns:
            for match in re.findall(pat, unescaped, re.I):
                self.media_items.append({
                    "url": urljoin(self.base_url, match),
                    "source": "JavaScript Player Config",
                    "type": "direct_video"
                })

    def _classify_type(self, url: str, mime: str = "") -> str:
        clean = url.lower().split("?")[0].split("#")[0]
        if ".m3u8" in clean or "mpegurl" in mime.lower():
            return "hls_stream"
        if ".mpd" in clean or "dash" in mime.lower():
            return "dash_stream"
        if clean.endswith((".mp4", ".mov", ".ts", ".m4v", ".flv", ".avi")):
            return "direct_video"
        if clean.endswith(".webm"):
            return "direct_video"
        if clean.endswith(".mkv"):
            return "direct_video"
        if any(p in clean for p in ["youtube.com", "youtu.be", "vimeo.com"]):
            return "embedded_player"
        return "page_video"


class VideoLinkFinder:
    """
    Stealth video link extractor that scans websites for embedded video streams,
    manifests, and players without triggering bot detection or IP blocks.
    """

    @staticmethod
    def build_stealth_headers(url: str) -> Dict[str, str]:
        """Constructs full modern desktop browser headers and origin-matching Referer."""
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}/" if parsed.netloc else "https://www.google.com/"

        # Use gzip, deflate by default. Only advertise 'br' (Brotli) if brotli library is available to decompress it.
        encodings = "gzip, deflate"
        try:
            import brotli  # type: ignore # noqa
            encodings = "gzip, deflate, br"
        except ImportError:
            pass

        return {
            "User-Agent": STEALTH_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": encodings,
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": origin,
        }

    @staticmethod
    def resolve_proxy(
        routing_mode: Optional[str] = "direct",
        custom_proxy: Optional[str] = None
    ) -> Optional[str]:
        """Resolves proxy URL based on routing mode (Direct, WARP, Tor, or Custom)."""
        if custom_proxy and custom_proxy.strip():
            return custom_proxy.strip()
        if routing_mode == "warp":
            active_warp = get_active_warp_proxy()
            return active_warp or "socks5://127.0.0.1:1080"
        if routing_mode == "tor":
            active_tor = get_active_tor_proxy()
            return active_tor or "socks5://127.0.0.1:9050"
        return None

    @classmethod
    async def find_links(
        cls,
        url: str,
        routing_mode: str = "direct",
        custom_proxy: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
        use_stealth: bool = True
    ) -> Dict[str, Any]:
        """
        Deeply inspects the webpage for video media links using:
        1. Direct media URL detection (if input is already a video link)
        2. Stealth HTTP DOM Parser (HTML5, OpenGraph, JSON-LD, HLS regex, iframes, video cards)
        3. Raw HTML regex scan (catches all media URLs regardless of HTML nesting or JS)
        4. yt-dlp extractor with playlist/feed support (for video catalogs, YouTube, and multi-video homepages)
        """
        url = url.strip()
        headers = cls.build_stealth_headers(url) if use_stealth else {"User-Agent": STEALTH_USER_AGENT}
        proxy_str = cls.resolve_proxy(routing_mode, custom_proxy)

        discovered: List[Dict[str, Any]] = []
        page_title = ""
        default_thumb = ""
        discovered_thumbs: List[str] = []

        # Fast-Path 1: Is the input URL itself a direct video or stream file?
        clean_input = url.lower().split("?")[0].split("#")[0]
        if clean_input.endswith(MEDIA_EXTENSIONS):
            filename = Path(unquote(urlparse(url).path)).name or "Direct Video Stream"
            discovered.append({
                "url": url,
                "title": filename,
                "source": "Direct Video URL",
                "type": "hls_stream" if clean_input.endswith(".m3u8") else "direct_video",
                "thumbnail": "",
            })
            page_title = filename

        # Engine 1: Stealth HTTP fetch & DOM parse
        html_text = ""
        try:
            client_kwargs: Dict[str, Any] = {
                "timeout": 15.0,
                "follow_redirects": True,
                "verify": False,  # Resilient against self-signed or proxy SSL cert issues
            }
            if proxy_str:
                client_kwargs["proxy"] = proxy_str

            async with httpx.AsyncClient(**client_kwargs) as client:
                resp = await client.get(url, headers=headers)
                content_type = resp.headers.get("content-type", "").lower()

                # If the server returned a direct video stream in response to the request
                if "video/" in content_type or "mpegurl" in content_type or "application/vnd.apple.mpegurl" in content_type:
                    filename = Path(unquote(urlparse(str(resp.url)).path)).name or "Direct Video Stream"
                    discovered.append({
                        "url": str(resp.url),
                        "title": filename,
                        "source": "Direct Video Stream (HTTP Response)",
                        "type": "hls_stream" if "mpegurl" in content_type else "direct_video",
                        "thumbnail": "",
                    })
                    if not page_title:
                        page_title = filename
                elif resp.status_code == 200:
                    html_text = resp.text
                    parser = MediaHTMLParser(base_url=str(resp.url))
                    parser.feed(html_text)

                    page_title = parser.og_title or parser.title or page_title
                    default_thumb = parser.og_image or parser.video_poster
                    discovered_thumbs = parser.discovered_thumbnails
                    discovered.extend(parser.media_items)

                    # Engine 2: Deep Raw HTML Regex Scan
                    # Catches any media links embedded in complex JavaScript, JSON, data attributes,
                    # or root-relative paths across the whole document
                    unescaped_html = html_text.replace(r"\/", "/").replace(r"\u0026", "&")
                    base_resp_url = str(resp.url)

                    # 1. Absolute and protocol-relative media URLs
                    for match in re.findall(
                        r'(?:https?:)?//[^\s"\'<>\(\)]+\.(?:mp4|webm|mkv|mov|ts|m3u8|mpd)(?:\?[^\s"\'<>\(\)]*)?',
                        unescaped_html,
                        re.I
                    ):
                        full_m = urljoin(base_resp_url, match)
                        discovered.append({
                            "url": full_m,
                            "source": "HTML Regex Match",
                            "type": "hls_stream" if ".m3u8" in full_m.lower() else "direct_video",
                            "thumbnail": default_thumb
                        })

                    # 2. Root-relative media paths in quotes
                    for match in re.findall(
                        r'["\'](/[^\s"\'<>\(\)]+\.(?:mp4|webm|mkv|mov|ts|m3u8|mpd)(?:\?[^\s"\'<>\(\)]*)?)["\']',
                        unescaped_html,
                        re.I
                    ):
                        full_m = urljoin(base_resp_url, match)
                        discovered.append({
                            "url": full_m,
                            "source": "HTML Relative Path Regex",
                            "type": "hls_stream" if ".m3u8" in full_m.lower() else "direct_video",
                            "thumbnail": default_thumb
                        })
        except Exception:
            pass

        # Engine 3: yt-dlp extractor to catch obfuscated/generic stream URLs, playlists, and homepage feeds
        def _run_ytdlp():
            # First try extract_playlist with max_entries to handle homepages, channels, and feeds
            try:
                playlist_data = YtDlpDownloader.extract_playlist(
                    url=url,
                    referer=url,
                    custom_proxy=proxy_str,
                    routing_mode=routing_mode,
                    cookies_from_browser=cookies_from_browser,
                    max_entries=60
                )
                if playlist_data and playlist_data.get("items"):
                    return {"type": "playlist", "data": playlist_data}
            except Exception:
                pass

            # Fallback to single video extract_info
            try:
                info = YtDlpDownloader.extract_info(
                    url=url,
                    referer=url,
                    custom_proxy=proxy_str,
                    routing_mode=routing_mode,
                    cookies_from_browser=cookies_from_browser
                )
                return {"type": "single", "data": info}
            except Exception:
                return None

        ytdlp_result = await asyncio.to_thread(_run_ytdlp)
        if ytdlp_result:
            rtype = ytdlp_result.get("type")
            rdata = ytdlp_result.get("data", {})

            if rtype == "playlist":
                # Handle multi-video homepage / feed / channel
                pl_title = rdata.get("title")
                if pl_title and not page_title:
                    page_title = pl_title

                for entry in rdata.get("items", []):
                    e_url = entry.get("url")
                    if e_url:
                        discovered.append({
                            "url": e_url,
                            "title": entry.get("title") or "Video",
                            "source": "yt-dlp Playlist / Feed",
                            "type": "page_video",
                            "thumbnail": entry.get("thumbnail") or default_thumb or "",
                            "duration": entry.get("duration")
                        })
            elif rtype == "single":
                # Handle single video metadata and stream formats
                yt_title = rdata.get("title") or page_title
                if not page_title and yt_title:
                    page_title = yt_title
                yt_thumb = rdata.get("thumbnail") or default_thumb

                # If yt-dlp resolved a direct video URL or stream
                formats = rdata.get("formats", [])
                direct_stream_url = rdata.get("url")
                if direct_stream_url:
                    discovered.append({
                        "url": direct_stream_url,
                        "title": yt_title,
                        "source": "yt-dlp Extractor (Direct Stream)",
                        "type": "direct_video" if ".m3u8" not in direct_stream_url else "hls_stream",
                        "thumbnail": yt_thumb,
                        "resolution": rdata.get("resolution") or ""
                    })

                # Add format streams
                for fmt in formats:
                    f_url = fmt.get("url")
                    if f_url and f_url != direct_stream_url and ("http" in f_url):
                        res_str = fmt.get("resolution") or f"{fmt.get('width', '')}x{fmt.get('height', '')}".strip("x")
                        ext = fmt.get("ext", "mp4").upper()
                        discovered.append({
                            "url": f_url,
                            "title": f"{yt_title} ({res_str or ext})",
                            "source": f"yt-dlp Format ({fmt.get('format_note') or ext})",
                            "type": "direct_video" if ".m3u8" not in f_url else "hls_stream",
                            "thumbnail": yt_thumb,
                            "resolution": res_str
                        })

        # Deduplicate links by normalized URL
        seen_urls: Set[str] = set()
        clean_links: List[Dict[str, Any]] = []

        # Helper to pair unassigned thumbnails by matching stem / filename
        def _find_best_thumb(item_url: str, item_title: str) -> str:
            path_stem = Path(unquote(urlparse(item_url).path)).stem.lower()
            if len(path_stem) > 3:
                for t in discovered_thumbs:
                    t_stem = Path(unquote(urlparse(t).path)).stem.lower()
                    if path_stem in t_stem or t_stem in path_stem:
                        return t
            return default_thumb or ""

        for item in discovered:
            raw_url = item.get("url", "").strip()
            if not raw_url or not raw_url.startswith(("http://", "https://")):
                continue

            # Strip fragments for deduplication
            norm_url = raw_url.split("#")[0]
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

            # Determine human-friendly format label
            clean_type = item.get("type", "page_video")
            lower_url = norm_url.lower().split("?")[0]
            fmt_label = "MP4"

            if ".m3u8" in lower_url:
                fmt_label = "HLS (.m3u8)"
            elif ".mpd" in lower_url:
                fmt_label = "DASH (.mpd)"
            elif lower_url.endswith(".webm"):
                fmt_label = "WEBM"
            elif lower_url.endswith(".mkv"):
                fmt_label = "MKV"
            elif lower_url.endswith(".mov"):
                fmt_label = "MOV"
            elif lower_url.endswith(".ts"):
                fmt_label = "TS"
            elif "youtube.com" in lower_url or "youtu.be" in lower_url:
                fmt_label = "YouTube"
            elif "vimeo.com" in lower_url:
                fmt_label = "Vimeo"
            elif clean_type == "embedded_player":
                fmt_label = "Embed"
            elif clean_type == "page_video":
                fmt_label = "Video Card"

            # Derive clean item title
            item_title = item.get("title", "").strip()
            if not item_title:
                path_name = Path(unquote(urlparse(norm_url).path)).name
                if path_name and "." in path_name and len(path_name) > 3:
                    item_title = path_name
                elif page_title:
                    item_title = f"{page_title} - Video {len(clean_links) + 1}"
                else:
                    item_title = f"Discovered Video {len(clean_links) + 1}"

            # Derive thumbnail
            item_thumb = item.get("thumbnail")
            if not item_thumb:
                item_thumb = _find_best_thumb(norm_url, item_title)

            clean_links.append({
                "url": norm_url,
                "title": item_title,
                "type": clean_type,
                "format": fmt_label,
                "source": item.get("source", "Webpage Media"),
                "thumbnail": item_thumb or "",
                "resolution": item.get("resolution") or ""
            })

        if not page_title:
            parsed = urlparse(url)
            page_title = parsed.netloc or "Discovered Webpage"

        return {
            "page_url": url,
            "page_title": page_title,
            "total_found": len(clean_links),
            "links": clean_links,
            "stealth_used": use_stealth,
            "proxy_used": proxy_str
        }
