from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import init_db, db_get_video
from app.config import cleanup_orphaned_temp_files
from app.routers import downloads, videos, websocket, system
from app.services.stream_auth import (
    is_stream_authorized,
    verify_stream_token,
    get_or_create_pin,
    verify_video_pin,
    is_client_localhost
)

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

@app.middleware("http")
async def enforce_desktop_boundaries(request: Request, call_next):
    """
    Strict security boundary:
    1. Localhost desktop user has full access to the dashboard, file system, settings, and downloads.
    2. External Wi-Fi devices (e.g. phones) are restricted STRICTLY to authorized video streaming:
       - Allowed: /watch/{video_id}, /api/videos/{video_id}/stream, /api/videos/{video_id}/download, /api/videos/{video_id}/verify-pin, /api/videos/{video_id}/qr.svg
       - Blocked: Desktop dashboard (/), file system browser (/api/system/*), download manager (/api/downloads/*), library management (/api/videos)
    """
    if is_client_localhost(request):
        return await call_next(request)

    path = request.url.path

    # Permitted endpoints for mobile phone streaming
    is_mobile_allowed = (
        path.startswith("/watch/")
        or (path.startswith("/api/videos/") and any(
            path.endswith(suffix) for suffix in ["/stream", "/download", "/verify-pin", "/qr.svg", "/share-link"]
        ))
    )

    if not is_mobile_allowed:
        # Non-localhost device trying to access root dashboard or static files
        if path == "/" or path.startswith("/assets") or path.endswith(".html") or not path.startswith("/api/"):
            return HTMLResponse(
                content="""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>🔒 Desktop Only · VideoManager</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      background: #0B0F19;
      color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 24px;
    }
    .card {
      background: #1E293B;
      border: 1px solid #334155;
      border-radius: 24px;
      padding: 36px 24px;
      max-width: 420px;
      text-align: center;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }
    .icon { font-size: 44px; margin-bottom: 16px; }
    h2 { font-size: 20px; font-weight: 700; margin-bottom: 10px; color: #FFF; }
    p { font-size: 13px; color: #94A3B8; line-height: 1.6; margin-bottom: 22px; }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(56, 189, 248, 0.12);
      color: #38BDF8;
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 9999px;
      padding: 7px 14px;
      font-size: 11px;
      font-weight: 600;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">💻🔒</div>
    <h2>Desktop Only Area</h2>
    <p>The VideoManager dashboard, computer file system, and download settings can only be accessed directly on your computer (localhost).</p>
    <div class="badge">📱 Mobile access is restricted to streaming only</div>
  </div>
</body>
</html>""",
                status_code=403
            )

        return JSONResponse(
            status_code=403,
            content={
                "detail": "Access denied: System settings, file system browsing, and management controls are strictly restricted to localhost."
            }
        )

    return await call_next(request)

# Initialize Database and clean orphaned fragments from previous runs
init_db()
cleanup_orphaned_temp_files()

# Include API Routers
app.include_router(downloads.router)
app.include_router(videos.router)
app.include_router(websocket.router)
app.include_router(system.router)


@app.get("/watch/{video_id}", response_class=HTMLResponse)
async def watch_mobile_page(video_id: str, request: Request):
    """
    Dedicated lightweight, high-performance mobile streaming player for
    iPhones and Androids connecting over local home Wi-Fi.
    Secured with HMAC-SHA256 tokens and 4-digit PIN authentication.
    """
    video = db_get_video(video_id)
    if not video:
        return HTMLResponse("<h2>Video not found or has been deleted.</h2>", status_code=404)

    token = request.query_params.get("token") or ""

    # Check if 'p' or 'pin' is passed in query parameters (seamless auto-login from QR code scan)
    p_param = request.query_params.get("p") or request.query_params.get("pin")
    if p_param and not token:
        valid, issued_tok = verify_video_pin(video_id, p_param)
        if valid and issued_tok:
            token = issued_tok

    # If client is not authorized (no valid token or cookie, and not localhost):
    if not is_stream_authorized(request, video_id) and not token:
        # Render the Security PIN Unlock Screen
        pin_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="theme-color" content="#0b0f19">
  <title>🔒 Wi-Fi Stream Protected · VideoManager</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
    body {{
      background: #0B0F19;
      color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #1F2937;
      border-radius: 24px;
      padding: 32px 24px;
      max-width: 420px;
      width: 100%;
      text-align: center;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
    }}
    .shield-badge {{
      width: 64px;
      height: 64px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.35);
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 18px;
      font-size: 30px;
    }}
    h2 {{ font-size: 19px; font-weight: 700; margin-bottom: 8px; color: #FFF; }}
    p {{ font-size: 13px; color: #94A3B8; line-height: 1.5; margin-bottom: 24px; }}
    .pin-input {{
      width: 100%;
      background: #0B0F19;
      border: 2px solid #334155;
      border-radius: 14px;
      padding: 16px;
      font-size: 28px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      letter-spacing: 10px;
      text-align: center;
      color: #38BDF8;
      outline: none;
      margin-bottom: 16px;
      transition: border 0.2s;
    }}
    .pin-input:focus {{ border-color: #38BDF8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }}
    .btn {{
      width: 100%;
      background: #0284C7;
      color: #FFF;
      border: none;
      border-radius: 14px;
      padding: 15px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
      transition: all 0.2s;
    }}
    .btn:active {{ transform: scale(0.98); }}
    .error-box {{
      color: #F87171;
      background: rgba(248, 113, 113, 0.1);
      border: 1px solid rgba(248, 113, 113, 0.25);
      border-radius: 10px;
      padding: 10px;
      font-size: 12px;
      margin-top: 14px;
      display: none;
    }}
    .hint {{
      margin-top: 18px;
      font-size: 11px;
      color: #64748B;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="shield-badge">🛡️</div>
    <h2>Wi-Fi Stream Protected</h2>
    <p>This stream is protected with end-to-end PIN encryption. Enter the 4-digit PIN shown on your computer screen to unlock and watch.</p>
    <form id="pinForm" onsubmit="submitPin(event)">
      <input
        type="tel"
        id="pinInput"
        class="pin-input"
        maxlength="6"
        placeholder="••••"
        autocomplete="one-time-code"
        autofocus
        required
      />
      <button type="submit" class="btn" id="unlockBtn">Unlock &amp; Watch</button>
      <div id="errMsg" class="error-box">❌ Incorrect PIN. Please check your computer screen.</div>
    </form>
    <div class="hint">
      🔒 Unauthorized devices on this Wi-Fi cannot view or sniff this video without your authorization PIN.
    </div>
  </div>
  <script>
    async function submitPin(e) {{
      e.preventDefault();
      const pin = document.getElementById('pinInput').value.trim();
      const err = document.getElementById('errMsg');
      const btn = document.getElementById('unlockBtn');
      if (!pin) return;

      btn.textContent = 'Verifying...';
      btn.disabled = true;
      err.style.display = 'none';

      try {{
        const res = await fetch('/api/videos/{video_id}/verify-pin', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ pin: pin }})
        }});
        const data = await res.json();
        if (data.success && data.token) {{
          // Authorized: set cookie and redirect to video player with token
          document.cookie = 'vm_token_{video_id}=' + data.token + '; path=/; max-age=86400; SameSite=Lax';
          window.location.href = window.location.pathname + '?token=' + encodeURIComponent(data.token);
        }} else {{
          err.style.display = 'block';
          btn.textContent = 'Unlock & Watch';
          btn.disabled = false;
        }}
      }} catch (errExp) {{
        err.style.display = 'block';
        btn.textContent = 'Unlock & Watch';
        btn.disabled = false;
      }}
    }}
  </script>
</body>
</html>"""
        return HTMLResponse(content=pin_html)

    # Client IS authorized! Render full player
    title = video.get("title") or "Streaming Video"
    duration = float(video.get("duration") or 0)
    dur_m, dur_s = divmod(int(duration), 60)
    duration_str = f"{dur_m}:{dur_s:02d}" if duration > 0 else "Live"
    size_mb = f"{video.get('file_size', 0) / (1024*1024):.1f} MB"
    res_str = video.get("resolution") or "HD Video"
    fmt_str = (video.get("file_format") or "mp4").upper()
    tok_query = f"?token={token}" if token else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="theme-color" content="#0b0f19">
  <title>{title} · VideoManager</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
    body {{
      background: #0B0F19;
      color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 16px;
    }}
    .container {{
      width: 100%;
      max-width: 580px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 4px 0;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 16px;
      color: #38BDF8;
      text-decoration: none;
    }}
    .wifi-badge {{
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      color: #10B981;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 4px 10px;
      border-radius: 9999px;
      font-weight: 600;
    }}
    .player-card {{
      background: #000;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
      border: 1px solid #1E293B;
      position: relative;
    }}
    video {{
      width: 100%;
      display: block;
      max-height: 65vh;
      outline: none;
      background: #000;
    }}
    .touch-controls {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: #0F172A;
      border-top: 1px solid #1E293B;
      gap: 8px;
    }}
    .seek-btn {{
      background: #1E293B;
      border: 1px solid #334155;
      color: #E2E8F0;
      font-size: 12px;
      font-weight: 600;
      padding: 7px 12px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
      user-select: none;
    }}
    .seek-btn:active {{
      background: #0284C7;
      color: #FFF;
      transform: scale(0.96);
    }}
    .speed-select {{
      background: #1E293B;
      border: 1px solid #334155;
      color: #38BDF8;
      font-size: 12px;
      font-weight: 600;
      padding: 7px 10px;
      border-radius: 8px;
      outline: none;
    }}
    .ripple-feedback {{
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      background: rgba(0, 0, 0, 0.7);
      color: #38BDF8;
      font-size: 14px;
      font-weight: 700;
      padding: 8px 16px;
      border-radius: 20px;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s ease;
      z-index: 10;
    }}
    .ripple-left {{ left: 20px; }}
    .ripple-right {{ right: 20px; }}
    .ripple-feedback.show {{ opacity: 1; }}
    .meta-card {{
      background: #111827;
      border: 1px solid #1F2937;
      border-radius: 18px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }}
    .title {{
      font-size: 16px;
      font-weight: 700;
      line-height: 1.4;
      color: #F8FAFC;
    }}
    .badges {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .badge {{
      font-size: 11px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      padding: 3px 8px;
      border-radius: 6px;
      background: #1E293B;
      color: #94A3B8;
      border: 1px solid #334155;
    }}
    .actions {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 4px;
    }}
    .btn {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 12px;
      border-radius: 12px;
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s;
    }}
    .btn-primary {{
      background: #0284C7;
      color: #FFF;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }}
    .btn-secondary {{
      background: #1E293B;
      color: #E2E8F0;
      border: 1px solid #334155;
    }}
    .footer-note {{
      text-align: center;
      font-size: 11px;
      color: #64748B;
      line-height: 1.5;
      padding: 8px 0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <a href="/" class="logo">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 8 6 4-6 4Z"/></svg>
        VideoManager
      </a>
      <div class="wifi-badge">
        🛡️ Encrypted Wi-Fi Stream
      </div>
    </div>

    <div class="player-card">
      <div id="rippleLeft" class="ripple-feedback ripple-left">⏪ -10s</div>
      <div id="rippleRight" class="ripple-feedback ripple-right">+10s ⏩</div>
      <video
        id="player"
        controls
        playsinline
        webkit-playsinline
        preload="auto"
        poster="/api/videos/{video_id}/thumbnail{tok_query}"
        src="/api/videos/{video_id}/stream{tok_query}"
      ></video>
      <div class="touch-controls">
        <button class="seek-btn" onclick="seekBy(-10)">⏪ -10s</button>
        <button class="seek-btn" onclick="seekBy(10)">+10s ⏩</button>
        <button class="seek-btn" onclick="seekBy(30)">+30s ⏭️</button>
        <select class="speed-select" onchange="changeSpeed(this.value)">
          <option value="1" selected>1.0x</option>
          <option value="1.25">1.25x</option>
          <option value="1.5">1.5x</option>
          <option value="2">2.0x</option>
        </select>
      </div>
    </div>

    <script>
      const video = document.getElementById('player');
      const rippleLeft = document.getElementById('rippleLeft');
      const rippleRight = document.getElementById('rippleRight');

      function seekBy(seconds) {{
        if (!video) return;
        video.currentTime = Math.max(0, Math.min(video.duration || Infinity, video.currentTime + seconds));
        showRipple(seconds > 0 ? rippleRight : rippleLeft);
      }}

      function changeSpeed(val) {{
        if (video) video.playbackRate = parseFloat(val);
      }}

      function showRipple(el) {{
        if (!el) return;
        el.classList.add('show');
        setTimeout(() => el.classList.remove('show'), 400);
      }}

      // Double-tap left/right gesture for mobile video seeking
      let lastTap = 0;
      let lastTapSide = '';
      video.addEventListener('touchend', function(e) {{
        const now = Date.now();
        const touch = e.changedTouches[0];
        const rect = video.getBoundingClientRect();
        const side = (touch.clientX - rect.left) < (rect.width / 2) ? 'left' : 'right';

        if (now - lastTap < 300 && lastTapSide === side) {{
          e.preventDefault();
          if (side === 'left') {{
            seekBy(-10);
          }} else {{
            seekBy(10);
          }}
          lastTap = 0;
        }} else {{
          lastTap = now;
          lastTapSide = side;
        }}
      }});
    </script>

    <div class="meta-card">
      <h1 class="title">{title}</h1>
      <div class="badges">
        <span class="badge">⏱️ {duration_str}</span>
        <span class="badge">💾 {size_mb}</span>
        <span class="badge">🎬 {res_str}</span>
        <span class="badge">📦 {fmt_str}</span>
      </div>

      <div class="actions">
        <a href="/api/videos/{video_id}/download{tok_query}" download class="btn btn-primary">
          ⬇️ Save Video to Phone
        </a>
      </div>
    </div>

    <div class="footer-note">
      Streaming directly from your computer over local home Wi-Fi.<br/>Zero cable transfers, zero cloud upload, zero mobile cellular data used.
    </div>
  </div>
</body>
</html>"""
    response = HTMLResponse(content=html)
    if token:
        response.set_cookie(f"vm_token_{video_id}", token, max_age=86400, httponly=True, samesite="lax")
    return response


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
