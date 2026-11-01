# 🎬 VideoManager

A modern, high-performance video download, streaming, and chunk-processing platform with a React dashboard and an extensible Python FastAPI backend.

---

## 🌟 Key Features

1. **Universal Downloader (yt-dlp Engine)**:
   - Supports 1,000+ video streaming sites (YouTube, Twitter/X, Instagram, TikTok, Vimeo, Reddit, Twitch, Rumble, Dailymotion, direct MP4/WebM).
   - Dynamic quality selector: Best, 1080p, 720p, 480p, or Audio-only (MP3/M4A).

2. **Custom Multi-Chunk Range Engine (`ChunkEngine`)**:
   - Downloads videos by splitting them into **N parallel byte-range chunks** (`Range: bytes=start-end`) using HTTP range headers.
   - Concurrently downloads each chunk to local part files (`chunk_0.part`, `chunk_1.part`, etc.).
   - Deterministic binary sequential merger that stitches chunks into the final video file with zero RAM bloat using streaming buffers.
   - Cleans up temporary chunks automatically upon successful merge.

3. **Segment List Stitcher (For HLS / Segmented Media)**:
   - For websites that stream media in discrete segments (e.g., `.ts` or `.m4s` chunks), you can provide a list of segment URLs.
   - VideoManager downloads each segment in sequence and stitches them together seamlessly.

4. **Selectable Download Directory (Visual Folder Picker)**:
   - Browse and choose any folder on your computer to save downloaded videos.
   - Set a global default destination or override per-download.
   - Real-time disk space free display.

5. **Real-Time Live Dashboard (WebSockets)**:
   - Real-time progress bar (percentage, download speed in MB/s, countdown ETA).
   - Live chunk progress breakdown (e.g., `Chunk 3 of 4 completed`, `Merging streams...`).
   - Active cancellation and failure recovery.

6. **Built-in Media Library & In-Browser Player**:
   - Stream downloaded videos with **HTTP Range headers** (supports seeking, scrubbing forward/back).
   - Download directly to computer, inspect file size, duration, resolution, or delete with one click.

---

## 🐳 Running with Docker (Recommended for Anyone)

VideoManager includes a multi-stage Docker setup with pre-installed `ffmpeg` and Python runtime.

### Using Docker Compose (Single Command):
```bash
docker compose up --build
```
* **Dashboard & API**: [http://localhost:8000](http://localhost:8000)
* **Downloaded Videos**: Stored in `./downloads` on your host machine automatically via volume mount.
* **Database & Config**: Persisted in `./data`.

To stop the container:
```bash
docker compose down
```

### Or using plain Docker CLI:
```bash
# 1. Build the image
docker build -t videomanager .

# 2. Run the container with a local downloads folder mounted
docker run -d \
  -p 8000:8000 \
  -v "$(pwd)/downloads:/app/storage/videos" \
  --name videomanager \
  videomanager
```

---

## 🚀 Running Locally (Without Docker)

### Option 1: Automated Script
```bash
./start.sh
```
This script checks dependencies, compiles the frontend, and launches the server at:
**[http://localhost:8000](http://localhost:8000)**

---

### Option 2: Running Backend & Frontend in Development Mode

#### 1. Backend:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
API Documentation (Swagger UI): **[http://localhost:8000/docs](http://localhost:8000/docs)**

#### 2. Frontend (Vite Dev Server with Hot-Reload):
```bash
cd frontend
npm install --cache /tmp/.npm-cache
npm run dev
```
Dashboard: **[http://localhost:5173](http://localhost:5173)**

---

## 🏗️ Architecture

```
VideoManager/
├── Dockerfile                   # Multi-stage production build (Node + Python + ffmpeg)
├── docker-compose.yml           # Pre-configured container & host volume mounts
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app & static file mounting
│   │   ├── config.py            # Storage paths & folder configuration
│   │   ├── database.py          # SQLite storage for video metadata & state
│   │   ├── models.py            # Pydantic data schemas
│   │   ├── routers/
│   │   │   ├── downloads.py     # Download & inspect API routes
│   │   │   ├── videos.py        # Stream (HTTP Range) & video management
│   │   │   ├── system.py        # Folder browsing & destination settings
│   │   │   └── websocket.py     # Real-time WebSocket connection
│   │   └── services/
│   │       ├── download_manager.py # Async task queue & event broadcaster
│   │       ├── chunk_engine.py  # Custom chunk downloader & binary merger
│   │       └── ytdlp_downloader.py # Universal yt-dlp integration
│   ├── storage/                 # Video & chunk storage
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main dashboard state & WS handler
│   │   ├── components/
│   │   │   ├── DownloadCard.tsx # URL input, format selector, folder destination
│   │   │   ├── FolderPickerModal.tsx # Interactive folder explorer dialog
│   │   │   ├── ActiveDownloads.tsx # Live progress cards with speed & ETA
│   │   │   ├── VideoGrid.tsx    # Video library cards & action triggers
│   │   │   ├── VideoPlayerModal.tsx # In-browser streaming player modal
│   │   │   ├── ChunkEngineExplainer.tsx # Architecture visualizer
│   │   │   └── Navbar.tsx       # Status bar, storage stats & folder picker trigger
│   │   ├── api.ts               # REST API client
│   │   └── types.ts             # TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── start.sh                     # Unified local startup script
└── README.md
```
