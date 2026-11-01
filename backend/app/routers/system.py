import os
import shutil
import asyncio
import socket
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.config import get_configured_download_dir, set_configured_download_dir, DEFAULT_VIDEOS_DIR
from app.models import SystemSettings, FolderBrowseResponse, FolderBrowseItem

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/settings")
async def get_settings():
    current_dir = get_configured_download_dir()
    total, used, free = shutil.disk_usage(str(current_dir))
    return {
        "download_folder": str(current_dir),
        "default_folder": str(DEFAULT_VIDEOS_DIR),
        "disk_free_bytes": free,
        "disk_total_bytes": total
    }

@router.post("/settings")
async def update_settings(settings: SystemSettings):
    folder_str = settings.download_folder.strip()
    if not folder_str:
        raise HTTPException(status_code=400, detail="Folder path cannot be empty")
    try:
        p = set_configured_download_dir(folder_str)
        test_file = p / ".write_test"
        test_file.touch()
        test_file.unlink()
        return {"success": True, "download_folder": str(p)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot use folder: {str(e)}")

@router.get("/browse-folders", response_model=FolderBrowseResponse)
async def browse_folders(path: Optional[str] = Query(None)):
    if not path or path == "~":
        target = Path.home()
    else:
        target = Path(path).expanduser().resolve()

    if not target.exists() or not target.is_dir():
        target = Path.home()

    folders = []
    try:
        for entry in os.scandir(str(target)):
            try:
                if entry.is_dir() and not entry.name.startswith("."):
                    folders.append(FolderBrowseItem(
                        name=entry.name,
                        path=entry.path,
                        is_dir=True
                    ))
            except PermissionError:
                continue
    except PermissionError:
        pass

    folders.sort(key=lambda x: x.name.lower())
    parent_path = str(target.parent) if target.parent != target else None
    return FolderBrowseResponse(
        current_path=str(target),
        parent_path=parent_path,
        folders=folders
    )

@router.get("/tor-status")
async def tor_status():
    """
    Check whether Tor is running locally by probing SOCKS5 on 127.0.0.1:9050.
    Also verifies connectivity through Tor by checking a lightweight endpoint.
    """
    host, port = "127.0.0.1", 9050

    # Step 1: check if the port is open (Tor SOCKS5 listener)
    def _port_open():
        try:
            s = socket.create_connection((host, port), timeout=2)
            s.close()
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            return False

    is_running = await asyncio.to_thread(_port_open)

    if not is_running:
        return {
            "running": False,
            "proxy": "socks5://127.0.0.1:9050",
            "message": "Tor is not running. Install Tor and start it: `brew install tor && tor`",
            "install_hint": "brew install tor && brew services start tor"
        }

    # Step 2: Try a real connection through the SOCKS5 proxy to check.torproject.org
    try:
        import httpx
        async with httpx.AsyncClient(
            proxies={"all://": "socks5://127.0.0.1:9050"},
            timeout=8.0
        ) as client:
            resp = await client.get("https://check.torproject.org/api/ip")
            data = resp.json()
            return {
                "running": True,
                "proxy": "socks5://127.0.0.1:9050",
                "is_tor": data.get("IsTor", False),
                "exit_ip": data.get("IP", "unknown"),
                "message": "Tor is running and working ✅" if data.get("IsTor") else "Tor port open but traffic may not route through Tor"
            }
    except Exception as e:
        return {
            "running": True,
            "proxy": "socks5://127.0.0.1:9050",
            "is_tor": None,
            "exit_ip": None,
            "message": f"Tor port is open but connectivity check failed: {str(e)}"
        }
