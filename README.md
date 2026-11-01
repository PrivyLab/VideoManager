# 🎬 VideoManager

A modern, high-performance video download, streaming, processing, and media management platform with a sleek React dashboard and an extensible Python FastAPI backend.

Built for power users who want full control over their media downloads, parallel chunking, anti-blocking network routing, automated link scraping, local Wi-Fi mobile streaming, and post-processing tools — with zero cloud lock-in.

---

## 🌟 Key Features

### 1. 🔍 Stealth Video Link Finder (Webpage Inspector)
- **Deep Webpage Scanner**: Paste any webpage or article URL to automatically detect and extract all embedded video streams without triggering scraper defenses.
- **Dual-Engine Extraction**:
  - **DOM & Manifest Parser**: Scans HTML5 `<video>`, `<source>`, OpenGraph (`og:video`), Twitter Cards (`twitter:player:stream`), Schema.org JSON-LD (`VideoObject`), HLS (`.m3u8`) playlists, DASH (`.mpd`) manifests, and direct media anchor links.
  - **yt-dlp Extractor Integration**: Resolves dynamic, obfuscated, and streaming player configurations (YouTube, Vimeo, Dailymotion, Bilibili, Streamtape, etc.).
- **Stealth & Anti-Bot Protection**:
  - Full modern desktop browser fingerprint (Chrome 124, Client Hints, Referer spoofing, session cookies).
  - Network IP shielding via Cloudflare WARP or Tor proxy routing to prevent IP rate-limiting.
  - Multi-select discovered links with 1-click batch queueing into VideoManager.

---

### 2. 🧩 1-Click Browser Bookmarklet ("Send to VideoManager")
- **Instant Web Integration**: Drag the **"Send to VideoManager"** button to your Chrome, Safari, Firefox, or Edge bookmarks bar.
- Whenever you are on any webpage with a video, click the bookmarklet to queue the download immediately.
- Injects a sleek dark-themed notification toast directly on the active webpage, executes a silent background API request, and seamlessly opens the dashboard if local server focus is needed.

---

### 3. 📋 Batch & Playlist Downloader
- **Bulk URL Input**: Paste 10–50 video links at once and let VideoManager queue, track, and download them sequentially with concurrency controls.
- **Interactive Playlist & Series Inspector**:
  - Paste any playlist or series link (YouTube, SoundCloud, series sets).
  - Previews all episodes and clips with thumbnails, durations, and uploaders.
  - Filter and checkbox-select only the episodes you want to download.

---

### 4. ⚡ Custom Multi-Chunk Range Engine (`ChunkEngine`)
- **Parallel Byte-Range Acceleration**: Splits video files into $N$ parallel HTTP byte-range chunks (`Range: bytes=start-end`) for maximum network throughput.
- **Deterministic Stream Assembly**: Merges chunks sequentially into the final media container with zero memory bloat using streaming buffers.
- **Direct Single-Stream Mode**: Automatically detects servers without Range support or unknown content lengths, streaming directly without invalid range errors or intermediate copy steps.
- **Resilient Fallback**: Automatically falls back between `ChunkEngine` and `YtDlpDownloader` if a host requires specialized extractor logic.

---

### 5. 📱 Encrypted Wi-Fi Mobile Streaming (QR Code Access)
- **Zero-Cable Phone Playback**: Click **"Watch on Phone"** on any video in your library to display a high-contrast vector QR code. Scanning it with an iPhone or Android camera immediately launches playback in your phone's browser over home Wi-Fi.
- **Smooth Mobile Seeking (RFC 7233 / 9110 HTTP Range)**: Instant scrub forward/backward on mobile browsers without buffering stalls.
- **FastStart Optimization**: Automatically moves the MP4 `moov` metadata atom to the beginning of the file so mobile browsers begin streaming immediately without buffering the entire file.
- **Cryptographic Security & PIN Shielding**:
  - HMAC-SHA256 signed session tokens prevent unauthorized network sniffing.
  - Optional 4-digit PIN screen prevents unauthorized Wi-Fi users from viewing or downloading streams.
  - Compact QR codes fit within standard Version 3 ($29 \times 29$) modules for instant scanning by mobile cameras.

---

### 6. 🔒 Strict Desktop & File System Boundaries
- **Localhost Boundary Isolation**: Full file system browsing (`/browse-folders`), destination folder configuration (`/settings`), and management APIs are strictly restricted to `localhost`.
- **Quarantined Mobile Access**: External devices on local Wi-Fi are strictly quarantined to video playback (`/watch/{id}`) and PIN verification. Any attempt to browse laptop files or access the dashboard from a phone is blocked with HTTP 403 Forbidden.

---

### 7. 🛠️ Built-in FFmpeg Media Post-Processing Tools
- **Video Trimmer**:
  - **Instant Stream Cut**: Sub-second lossless cutting with zero re-encoding.
  - **Frame-Accurate Cut**: Re-encodes keyframes for exact time-boundary splits.
  - **Audio Snippet**: Trim and export the exact segment as an MP3 audio track.
- **Audio Track Extractor**: Convert videos to MP3, M4A, AAC, or WAV with selectable bitrates (128k, 192k, 256k, 320k).
- **Video Compressor**: Compress large media files (High, Balanced, or Maximum Compression) or specify an exact target size (e.g. 25 MB for Discord/email).
- **GIF Generator**: Create animated GIFs from video clips with custom FPS, resolution, and repeat settings.
- **Multi-Video Stitcher**: Merge and concatenate multiple downloaded clips into a single video file.
- **Bulk Video Library Management & Deletion**:
  - **Multi-Select Mode**: Select multiple videos across completed, failed, or cancelled downloads.
  - **Bulk Deletion**: Delete all selected videos and purge their stored media files from the disk in a single click with confirmation protection.
  - **Cancel All Downloads**: One-click bulk cancellation for all active or queued downloads in progress.

---

### 8. 🛡️ Network Routing & Anti-Blocking Suite
- **Multi-Mode Network Routing**:
  - **Direct**: Standard connection via host network.
  - **Cloudflare WARP**: Route requests through Cloudflare's edge proxy network to mask your home IP.
  - **Tor SOCKS5**: Route through the Tor anonymity network.
  - **Custom Proxy**: Supports HTTP, HTTPS, and SOCKS5 proxies (`socks5://user:pass@host:port`).
- **Browser Cookie Sessions**: Import session cookies directly from your local browser (**Chrome, Safari, Firefox, Brave, Edge**) to download videos behind logins or age-gates.
- **Live Network Diagnostic**: Probe Cloudflare WARP and Tor container statuses with real-time indicators.

---

## 🐳 Running with Docker (Recommended)

VideoManager includes a multi-stage production Docker setup with pre-installed `ffmpeg` and Python runtime.

### Using Docker Compose:
```bash
docker compose up --build
```
* **Dashboard & API**: [http://localhost:8000](http://localhost:8000)
* **Downloaded Videos**: Stored in `./downloads` on your host machine via volume mount.
* **Database & Config**: Persisted in `./data`.

To stop the container:
```bash
docker compose down
```

### Or using plain Docker CLI:
```bash
# 1. Build the image
docker build -t videomanager .

# 2. Run container with mounted downloads
docker run -d \
  -p 8000:8000 \
  -v "$(pwd)/downloads:/app/storage/videos" \
  --name videomanager \
  videomanager
```

---

## ⚙️ Configuration & Environment Variables

VideoManager supports configuring the video download directory via `.env` or the web UI:

* **`.env` Precedence**: If a `.env` file is present in your project root or `backend/` directory, VideoManager takes the download video destination from `.env` instead of `settings.json`.
  ```bash
  # .env example
  DOWNLOAD_DIR=/Users/yourname/Downloads/Videos
  TOR_PROXY=socks5://127.0.0.1:9050
  WARP_PROXY=socks5://127.0.0.1:1080
  ```
* **Web UI Settings**: If `.env` is not present, destination folder preferences are persisted in `storage/settings.json` and can be changed anytime via the folder picker in the dashboard.

---

## 🚀 Running Locally (Without Docker)

### Option 1: Automated Script
```bash
./start.sh
```
This script checks dependencies, compiles the frontend, and launches the server at:
**[http://localhost:8000](http://localhost:8000)**

---

### Option 2: Manual Development Mode

#### 1. Backend:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
* **Interactive API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 2. Frontend (Vite Dev Server with Hot-Reload):
```bash
cd frontend
npm install
npm run dev
```
* **Frontend Dev Server**: [http://localhost:5173](http://localhost:5173)

---

## 🏗️ Architecture & Project Structure

```
VideoManager/
├── Dockerfile                      # Multi-stage production container build (Node + Python + ffmpeg)
├── docker-compose.yml              # Pre-configured container & host volume mounts
├── start.sh                        # Automated local startup script
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, security middleware & mobile player
│   │   ├── config.py               # Storage paths, proxy config & folder management
│   │   ├── database.py             # SQLite storage for video metadata, queue & PIN security
│   │   ├── models.py               # Pydantic data schemas & request models
│   │   ├── routers/
│   │   │   ├── downloads.py        # Single, batch, playlist inspect & link finder routes
│   │   │   ├── videos.py           # HTTP range streaming, library management & QR generator
│   │   │   ├── system.py           # Localhost file browsing & destination folder settings
│   │   │   └── websocket.py        # Real-time WebSocket connection for live downloads
│   │   └── services/
│   │       ├── download_manager.py # Async task orchestration, queueing & event broadcasts
│   │       ├── chunk_engine.py     # Custom multi-chunk range engine & direct stream fallback
│   │       ├── video_link_finder.py# Stealth HTML5/DOM/manifest extractor & proxy router
│   │       ├── stream_auth.py      # HMAC-SHA256 stream tokens & 4-digit PIN security
│   │       ├── qr_generator.py     # ISO/IEC 18004 standard SVG QR code generator
│   │       ├── faststart.py        # MP4 moov atom re-positioning for instant mobile seeking
│   │       ├── video_stitcher.py   # Multi-clip FFmpeg concatenation engine
│   │       ├── media_tools.py      # Trimming, audio extraction, compression & GIF creation
│   │       └── ytdlp_downloader.py # Universal yt-dlp wrapper with real-time callbacks
│   ├── tests/
│   │   └── test_backend.py         # Comprehensive unit and integration test suite
│   ├── storage/                    # Video library & temporary chunk storage
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main application state & WebSocket event dispatcher
│   │   ├── components/
│   │   │   ├── Navbar.tsx          # Top navigation, storage metrics & modal triggers
│   │   │   ├── DownloadCard.tsx    # URL input, batch mode, playlist inspector & options
│   │   │   ├── ActiveDownloads.tsx # Live progress cards with speed, chunk breakdown & ETA
│   │   │   ├── VideoGrid.tsx       # Video cards, search/filter & media tool actions
│   │   │   ├── VideoPlayerModal.tsx# In-browser streaming player modal with scrub controls
│   │   │   ├── LinkFinderModal.tsx # Stealth video link finder & batch extractor
│   │   │   ├── MobileStreamModal.tsx# QR code display, Wi-Fi stream URL & PIN controls
│   │   │   ├── MediaToolsModal.tsx # Video trimming, audio extraction, compression & GIF tools
│   │   │   ├── VideoStitchModal.tsx# Visual multi-video stitcher & re-order interface
│   │   │   ├── BookmarkletModal.tsx# 1-Click browser bookmarklet installer
│   │   │   ├── FolderPickerModal.tsx# Interactive desktop folder explorer
│   │   │   └── ChunkEngineExplainer.tsx# Chunking architecture documentation & diagrams
│   │   ├── api.ts                  # REST API client & helpers
│   │   └── types.ts                # TypeScript interfaces & definitions
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## 🧪 Testing & Verification

The backend includes a comprehensive test suite covering all operational modules:

```bash
PYTHONPATH=backend ./backend/venv/bin/python3 backend/tests/test_backend.py
```

### Test Coverage:
- `Database operations test`: CRUD, status updates, metadata retention.
- `Chunk engine merge test`: Binary stream merging and buffer validation.
- `Download folder configuration test`: Dynamic path validation and directory setup.
- `Video stitching test`: FFmpeg concatenation of test clips.
- `Media Tools test`: Audio extraction (MP3), video compression, and GIF generation.
- `Video Trimmer test`: Stream-copy fast cut and frame-accurate re-encoding.
- `Batch & Playlist Queue Manager test`: Batch queue ordering and playlist parsing.
- `QR Code & Wi-Fi Mobile Streaming test`: SVG QR code generation and Wi-Fi LAN IP discovery.
- `HTTP Byte-Range Mobile Seeking test`: HEAD, single-byte probe, and Range slice responses.
- `Wi-Fi Stream Cryptographic Encryption & PIN Security test`: HMAC token generation and PIN verification.
- `Single direct video stream test`: Non-range streaming and Content-Length handling.
- `Desktop Security & Wi-Fi Boundaries test`: Localhost permission checks and external client 403 blocks.
- `Video Link Finder test`: HTML5/DOM parsing, OpenGraph extraction, stealth headers, and proxy routing.

To run the frontend test and build check:
```bash
cd frontend && npm run build
```

---

## 🛡️ Security Model

| Endpoint / Capability | Localhost Desktop | Phone / Wi-Fi Client |
|---|---|---|
| **Web Dashboard (`/`)** | ✅ Full Access | ❌ **Blocked with 403 Screen** |
| **File System Browsing (`/browse-folders`)** | ✅ Full Access | ❌ **403 Forbidden** |
| **Download Destination Settings (`/settings`)** | ✅ Full Access | ❌ **403 Forbidden** |
| **Initiate Downloads (`/downloads`)** | ✅ Full Access | ❌ **403 Forbidden** |
| **Video Link Finder (`/find-links`)** | ✅ Full Access | ❌ **403 Forbidden** |
| **Full Video Library (`/videos`)** | ✅ Full Access | ❌ **403 Forbidden** |
| **Watch Shared Video (`/watch/{id}`)** | ✅ Full Access | ✅ Allowed (**Requires PIN / Token**) |
| **Stream Video Bytes (`/stream`)** | ✅ Full Access | ✅ Allowed (**Requires PIN / Token**) |

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
