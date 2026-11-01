import os
import shutil
import asyncio
import socket
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.config import (
    get_configured_download_dir,
    set_configured_download_dir,
    DEFAULT_VIDEOS_DIR,
    RUNNING_IN_DOCKER,
    WARP_PROXY_ENV,
    TOR_PROXY_ENV,
)
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

@router.get("/network-status")
async def network_status():
    """
    Returns Docker status and probing results for both Cloudflare WARP and Tor SOCKS5 proxies.
    """
    def _check_warp():
        if WARP_PROXY_ENV and WARP_PROXY_ENV.strip():
            url = WARP_PROXY_ENV.strip()
            parts = url.replace("socks5://", "").replace("http://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 1080
            try:
                s = socket.create_connection((host, port), timeout=0.6)
                s.close()
                return {"available": True, "proxy": url, "source": "Docker WARP Service", "is_active": True, "message": "Cloudflare WARP (Docker) Active ✅"}
            except Exception:
                return {"available": False, "proxy": url, "source": "Docker WARP Service", "is_active": False, "message": "Docker WARP container starting..."}

        for host, port in [("warp", 1080), ("127.0.0.1", 1080)]:
            try:
                s = socket.create_connection((host, port), timeout=0.6)
                s.close()
                return {"available": True, "proxy": f"socks5://{host}:{port}", "source": "Cloudflare WARP", "is_active": True, "message": "Cloudflare WARP Active ✅"}
            except Exception:
                pass
        return {"available": False, "proxy": "socks5://warp:1080", "source": "Cloudflare WARP", "is_active": False, "message": "Available in Docker mode (`docker compose up`)."}

    def _check_tor():
        if TOR_PROXY_ENV and TOR_PROXY_ENV.strip():
            url = TOR_PROXY_ENV.strip()
            parts = url.replace("socks5://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 9050
            try:
                s = socket.create_connection((host, port), timeout=0.6)
                s.close()
                return {"available": True, "proxy": url, "source": "Docker Tor Service", "is_active": True, "message": "Tor Network (Docker) Active ✅"}
            except Exception:
                return {"available": False, "proxy": url, "source": "Docker Tor Service", "is_active": False, "message": "Docker Tor container starting..."}

        for host, port, label in [("127.0.0.1", 9150, "Tor Browser"), ("127.0.0.1", 9050, "Tor Daemon / Docker"), ("tor", 9050, "Docker Tor Container")]:
            try:
                s = socket.create_connection((host, port), timeout=0.6)
                s.close()
                return {"available": True, "proxy": f"socks5://{host}:{port}", "source": label, "is_active": True, "message": f"{label} Active ✅"}
            except Exception:
                pass
        return {"available": False, "proxy": "socks5://127.0.0.1:9150", "source": "Tor", "is_active": False, "message": "Tor not running. Open Tor Browser or start Docker Compose."}

    loop = asyncio.get_running_loop()
    warp_res, tor_res = await asyncio.gather(
        loop.run_in_executor(None, _check_warp),
        loop.run_in_executor(None, _check_tor)
    )

    return {
        "in_docker": RUNNING_IN_DOCKER,
        "warp": warp_res,
        "tor": tor_res,
    }

@router.get("/tor-status")
async def tor_status():
    """
    Check whether Tor is running by probing:
    1. Port 9150 (Tor Browser Mac App)
    2. Port 9050 (Docker or local Tor daemon)
    3. TOR_PROXY environment variable
    """
    import socket
    from app.config import TOR_PROXY_ENV

    def _probe_proxy():
        if TOR_PROXY_ENV and TOR_PROXY_ENV.strip():
            return ("configured", 0, TOR_PROXY_ENV.strip(), "Docker Compose")

        candidates = [
            ("127.0.0.1", 9150, "socks5://127.0.0.1:9150", "Tor Browser"),
            ("127.0.0.1", 9050, "socks5://127.0.0.1:9050", "Tor Daemon / Docker"),
            ("tor", 9050, "socks5://tor:9050", "Docker Tor Container"),
        ]
        for host, port, proxy_url, label in candidates:
            try:
                s = socket.create_connection((host, port), timeout=0.6)
                s.close()
                return (host, port, proxy_url, label)
            except Exception:
                pass
        return None

    probed = await asyncio.to_thread(_probe_proxy)

    if not probed:
        return {
            "running": False,
            "proxy": "socks5://127.0.0.1:9150",
            "source": None,
            "message": "Tor is not active.",
            "install_hint": "Launch Tor Browser on your Mac (it runs on port 9150), or run `docker compose up`."
        }

    host, port, proxy_url, label = probed

    # Try checking exit IP through the proxy
    try:
        import httpx
        async with httpx.AsyncClient(
            proxies={"all://": proxy_url},
            timeout=8.0
        ) as client:
            resp = await client.get("https://check.torproject.org/api/ip")
            data = resp.json()
            is_tor = data.get("IsTor", False)
            exit_ip = data.get("IP", "unknown")
            return {
                "running": True,
                "proxy": proxy_url,
                "source": label,
                "is_tor": is_tor,
                "exit_ip": exit_ip,
                "message": f"Connected via {label} ({'Tor confirmed' if is_tor else 'Proxy ready'}) ✅"
            }
    except Exception as e:
        return {
            "running": True,
            "proxy": proxy_url,
            "source": label,
            "is_tor": True,  # Port opened successfully
            "exit_ip": "connected",
            "message": f"{label} is active on {proxy_url} ✅"
        }
