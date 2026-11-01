from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.download_manager import download_manager
from app.services.stream_auth import is_client_localhost

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/downloads")
async def websocket_downloads(websocket: WebSocket):
    if not is_client_localhost(websocket):
        await websocket.close(code=1008, reason="Desktop only")
        return

    await websocket.accept()
    await download_manager.register_ws(websocket)
    try:
        while True:
            # Keep connection alive & listen for client pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        download_manager.unregister_ws(websocket)
    except Exception:
        download_manager.unregister_ws(websocket)

