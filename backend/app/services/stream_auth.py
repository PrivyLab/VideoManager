import base64
import hashlib
import hmac
import os
import random
import secrets
import time
from pathlib import Path
from typing import Optional, Tuple
from fastapi import Request

from app.config import VIDEOS_DIR
from app.database import db_get_stream_security, db_set_stream_security

# Persistent server secret for HMAC-SHA256 signature signing
SECRET_FILE = VIDEOS_DIR.parent / ".stream_secret"


def _get_secret_key() -> str:
    try:
        if SECRET_FILE.exists():
            key = SECRET_FILE.read_text().strip()
            if key and len(key) >= 32:
                return key
        # Generate a new cryptographic secret key
        SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        new_key = secrets.token_hex(32)
        SECRET_FILE.write_text(new_key)
        return new_key
    except Exception:
        return "vm_default_secret_key_9283748291048291"


SECRET_KEY = _get_secret_key()


def generate_stream_token(video_id: str, expires_in_seconds: int = 86400) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 token.
    Valid for `expires_in_seconds` (default 24h).
    """
    exp = int(time.time()) + expires_in_seconds
    salt = secrets.token_hex(4)
    data = f"{video_id}:{exp}:{salt}"
    sig = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()[:24]
    raw = f"{data}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def verify_stream_token(token: Optional[str], video_id: str) -> bool:
    """
    Verifies that the provided token was signed with the server's secret key,
    matches the requested video_id, and has not expired.
    """
    if not token or not token.strip():
        return False

    tok = token.strip()
    try:
        pad = len(tok) % 4
        dec = base64.urlsafe_b64decode(tok + ("=" * (4 - pad) if pad else "")).decode()
        parts = dec.split(":")
        if len(parts) != 4:
            return False

        t_vid, t_exp, t_salt, t_sig = parts
        if t_vid != video_id:
            return False

        if int(t_exp) < time.time():
            return False  # Expired

        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{t_vid}:{t_exp}:{t_salt}".encode(),
            hashlib.sha256
        ).hexdigest()[:24]

        return hmac.compare_digest(t_sig, expected_sig)
    except Exception:
        return False


def get_or_create_pin(video_id: str) -> Tuple[str, bool]:
    """Returns (pin, pin_enabled) for the given video_id, creating one if not set."""
    record = db_get_stream_security(video_id)
    if record:
        return str(record["pin"]), bool(record.get("pin_enabled", 1))

    # Generate a user-friendly 4-digit PIN (e.g. 4819)
    new_pin = f"{random.randint(1000, 9999)}"
    db_set_stream_security(video_id, new_pin, pin_enabled=True)
    return new_pin, True


def set_pin_config(video_id: str, pin: Optional[str] = None, pin_enabled: Optional[bool] = None) -> Tuple[str, bool]:
    """Updates the PIN or enable/disable state for a video."""
    current_pin, current_enabled = get_or_create_pin(video_id)
    updated_pin = pin.strip() if pin and pin.strip() else current_pin
    updated_enabled = pin_enabled if pin_enabled is not None else current_enabled
    db_set_stream_security(video_id, updated_pin, pin_enabled=updated_enabled)
    return updated_pin, updated_enabled


def verify_video_pin(video_id: str, candidate_pin: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a submitted PIN.
    If valid, returns (True, signed_stream_token).
    """
    expected_pin, pin_enabled = get_or_create_pin(video_id)
    if not pin_enabled:
        # PIN protection is disabled for this video
        return True, generate_stream_token(video_id)

    if hmac.compare_digest(str(candidate_pin).strip(), expected_pin.strip()):
        token = generate_stream_token(video_id)
        return True, token

    return False, None


def is_client_localhost(request: Request) -> bool:
    """Checks if the request is originating from the local machine (desktop user)."""
    client_host = getattr(request.client, "host", "") if request.client else ""
    return client_host in ("127.0.0.1", "::1", "localhost", "testclient")


def is_stream_authorized(request: Request, video_id: str) -> bool:
    """
    Checks if a streaming request is authorized.
    1. Always allows local machine desktop user (localhost / 127.0.0.1).
    2. For external Wi-Fi clients (e.g. 192.168.x.x):
       - Checks ?token=... query parameter
       - Checks Authorization: Bearer <token>
       - Checks X-Stream-Token: <token>
       - Checks vm_token_{video_id} or vm_stream_token cookie
    """
    if is_client_localhost(request):
        return True

    # 1. Query parameter token
    q_token = request.query_params.get("token")
    if verify_stream_token(q_token, video_id):
        return True

    # 2. Cookie token
    cookie_token = (
        request.cookies.get(f"vm_token_{video_id}")
        or request.cookies.get("vm_stream_token")
    )
    if verify_stream_token(cookie_token, video_id):
        return True

    # 3. Header token
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()
        if verify_stream_token(bearer_token, video_id):
            return True

    x_token = request.headers.get("x-stream-token")
    if verify_stream_token(x_token, video_id):
        return True

    return False

