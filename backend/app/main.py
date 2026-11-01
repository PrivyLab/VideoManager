from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db
from app.routers import downloads, videos, websocket, system

app = FastAPI(
    title="VideoManager API",
    description="High-performance video downloading, chunking, merging, and streaming engine.",
    version="1.0.0"
)

# Enable CORS for local Vite dev server and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
init_db()

# Include API Routers
app.include_router(downloads.router)
app.include_router(videos.router)
app.include_router(websocket.router)
app.include_router(system.router)

# Mount frontend static build if it exists
candidates = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),
]
for dist in candidates:
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
        break
