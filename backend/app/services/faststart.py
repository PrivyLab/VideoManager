import asyncio
import os
import shutil
import struct
from pathlib import Path
from typing import Optional


def is_mp4_faststart(path: Path) -> bool:
    """
    Checks if an MP4/MOV/M4V container has its 'moov' atom located BEFORE the 'mdat' atom.
    When 'moov' is at the start (FastStart / Web Optimized), mobile browsers (iOS Safari, Android Chrome)
    can seek forward and backward instantly without having to download or buffer the entire file first.
    """
    if not path.is_file():
        return False

    try:
        with open(path, "rb") as f:
            offset = 0
            file_size = path.stat().st_size
            found_mdat = False

            while offset < file_size:
                f.seek(offset)
                header = f.read(8)
                if len(header) < 8:
                    break

                atom_size, atom_type = struct.unpack(">I4s", header)
                if atom_size == 1:
                    extended = f.read(8)
                    if len(extended) < 8:
                        break
                    atom_size = struct.unpack(">Q", extended)[0]
                elif atom_size == 0:
                    atom_size = file_size - offset

                atom_name = atom_type.decode("latin-1", errors="replace")

                if atom_name == "moov":
                    # If we haven't seen mdat yet, moov is at the beginning -> FastStart enabled!
                    return not found_mdat
                elif atom_name == "mdat":
                    found_mdat = True
                    # mdat encountered before moov -> moov is at the end of the file!
                    return False

                if atom_size <= 0:
                    break
                offset += atom_size

        return False
    except Exception:
        return False


async def ensure_faststart(path: Path) -> Path:
    """
    Ensures the MP4 file has 'moov' atom at the beginning.
    Uses ffmpeg with lossless '-c copy -movflags +faststart'.
    Takes only ~50-150ms since no re-encoding is performed.
    """
    if not path.is_file():
        return path

    ext = path.suffix.lower()
    if ext not in [".mp4", ".m4v", ".mov"]:
        return path

    # If already faststart, return immediately (zero overhead, < 0.1ms)
    if is_mp4_faststart(path):
        return path

    ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if not os.path.exists(ffmpeg_bin):
        return path

    temp_path = path.with_name(f"{path.stem}__faststart{path.suffix}")

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(temp_path),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if proc.returncode == 0 and temp_path.exists() and temp_path.stat().st_size > 0:
            temp_path.replace(path)
            return path
        elif temp_path.exists():
            temp_path.unlink()
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

    return path

