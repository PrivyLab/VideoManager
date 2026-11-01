import os
import re
import socket
import subprocess
from typing import List, Optional
from pathlib import Path


def get_local_wifi_ip() -> str:
    """
    Auto-detects the host machine's active local Wi-Fi / LAN IP address
    so devices on the same home network can connect.
    """
    # 1. Try ifconfig output on macOS / Linux
    try:
        out = subprocess.check_output(["ifconfig"], text=True)
        for line in out.splitlines():
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                ip = m.group(1)
                # Ignore loopback, docker bridge, and link-local auto-ip
                if (
                    not ip.startswith("127.")
                    and not ip.startswith("172.17.")
                    and not ip.startswith("169.254.")
                ):
                    return ip
    except Exception:
        pass

    # 2. Try routing socket query
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass

    # 3. Fallback to hostname resolution
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if not host_ip.startswith("127."):
            return host_ip
    except Exception:
        pass

    return "127.0.0.1"


# --- ISO/IEC 18004 Standard QR Code Generator ---
# Precomputed Galois Field GF(256) tables for Reed-Solomon encoding
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _EXP[_i + 255] = _x
    _LOG[_x] = _i
    _x = (_x << 1) ^ (0x11D if (_x & 0x80) else 0)


def _gmult(a: int, b: int) -> int:
    return _EXP[_LOG[a] + _LOG[b]] if a and b else 0


def _rs_encode(data: List[int], nsym: int) -> List[int]:
    gen = [1]
    for i in range(nsym):
        new_gen = [0] * (len(gen) + 1)
        for j, c in enumerate(gen):
            new_gen[j] ^= c
            new_gen[j + 1] ^= _gmult(c, _EXP[i])
        gen = new_gen
    msg = list(data) + [0] * nsym
    for i in range(len(data)):
        lead = msg[i]
        if lead != 0:
            for j in range(len(gen)):
                msg[i + j] ^= _gmult(gen[j], lead)
    return msg[len(data) :]


def generate_qr_matrix(text: str) -> List[List[int]]:
    """Generates standard QR code matrix (0=light, 1=dark)."""
    raw = text.encode("utf-8")

    # Select appropriate version for Level L error correction
    if len(raw) <= 17:
        v, size, data_cap, nsym, align = 1, 21, 19, 7, []
    elif len(raw) <= 32:
        v, size, data_cap, nsym, align = 2, 25, 34, 10, [18]
    elif len(raw) <= 53:
        v, size, data_cap, nsym, align = 3, 29, 55, 15, [22]
    elif len(raw) <= 78:
        v, size, data_cap, nsym, align = 4, 33, 80, 20, [26]
    elif len(raw) <= 106:
        v, size, data_cap, nsym, align = 5, 37, 108, 26, [30]
    else:
        v, size, data_cap, nsym, align = 6, 41, 134, 28, [34]

    # Data bitstream assembly (Byte mode = 0100)
    bits = [0, 1, 0, 0]
    for i in range(7, -1, -1):
        bits.append((len(raw) >> i) & 1)
    for byte in raw:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    for _ in range(min(4, data_cap * 8 - len(bits))):
        bits.append(0)
    while len(bits) % 8 != 0:
        bits.append(0)

    bytes_data = []
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | bits[i + j]
        bytes_data.append(b)

    pad = [0xEC, 0x11]
    p_idx = 0
    while len(bytes_data) < data_cap:
        bytes_data.append(pad[p_idx % 2])
        p_idx += 1

    ec = _rs_encode(bytes_data, nsym)
    all_codewords = bytes_data + ec

    mat = [[0] * size for _ in range(size)]
    res = [[False] * size for _ in range(size)]

    # 1. Place Finder Patterns (7x7) + Separators
    def set_finder(r0: int, c0: int):
        for r in range(r0 - 1, r0 + 8):
            for c in range(c0 - 1, c0 + 8):
                if 0 <= r < size and 0 <= c < size:
                    mat[r][c] = 0
                    res[r][c] = True
        for r in range(r0, r0 + 7):
            for c in range(c0, c0 + 7):
                v_bit = 1 if (
                    r == r0
                    or r == r0 + 6
                    or c == c0
                    or c == c0 + 6
                    or (r0 + 2 <= r <= r0 + 4 and c0 + 2 <= c <= c0 + 4)
                ) else 0
                mat[r][c] = v_bit
                res[r][c] = True

    set_finder(0, 0)
    set_finder(0, size - 7)
    set_finder(size - 7, 0)

    # 2. Place Alignment Patterns
    if align:
        for ar in align:
            for ac in align:
                if res[ar][ac]:
                    continue
                for r in range(ar - 2, ar + 3):
                    for c in range(ac - 2, ac + 3):
                        v_bit = 1 if (
                            r == ar - 2
                            or r == ar + 2
                            or c == ac - 2
                            or c == ac + 2
                            or (r == ar and c == ac)
                        ) else 0
                        mat[r][c] = v_bit
                        res[r][c] = True

    # 3. Timing patterns
    for i in range(size):
        if not res[6][i]:
            mat[6][i] = 1 if (i % 2 == 0) else 0
            res[6][i] = True
        if not res[i][6]:
            mat[i][6] = 1 if (i % 2 == 0) else 0
            res[i][6] = True

    # 4. Dark module
    dark_r = 4 * v + 9
    mat[dark_r][8] = 1
    res[dark_r][8] = True

    # 5. Reserve format info zones
    for i in range(9):
        res[8][i] = True
        res[i][8] = True
    for i in range(8):
        res[8][size - 1 - i] = True
        res[size - 1 - i][8] = True

    # 6. Place Data Codewords (zig-zag traversal)
    bit_idx = 0
    all_bits = []
    for cw in all_codewords:
        for i in range(7, -1, -1):
            all_bits.append((cw >> i) & 1)

    dir_up = True
    for c in range(size - 1, 0, -2):
        if c <= 6:
            c -= 1  # Skip timing column
        col_pair = [c, c - 1]
        row_range = range(size - 1, -1, -1) if dir_up else range(size)
        for r in row_range:
            for cc in col_pair:
                if not res[r][cc]:
                    b = all_bits[bit_idx] if bit_idx < len(all_bits) else 0
                    bit_idx += 1
                    # Mask pattern 0: (r + cc) % 2 == 0
                    if (r + cc) % 2 == 0:
                        b ^= 1
                    mat[r][cc] = b
        dir_up = not dir_up

    # 7. Place Format Info: Level L + Mask 0 = 0x77C4 (111011111000100)
    fmt_bits = [(0x77C4 >> i) & 1 for i in range(14, -1, -1)]
    seq1 = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
    ]
    for (r, c), bit in zip(seq1, fmt_bits):
        mat[r][c] = bit

    seq2 = [
        (size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
        (size - 5, 8), (size - 6, 8), (size - 7, 8),
    ] + [
        (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5),
        (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1),
    ]
    for (r, c), bit in zip(seq2, fmt_bits):
        mat[r][c] = bit

    return mat


def generate_qr_svg(text: str, border: int = 4, scale: int = 8) -> str:
    """Renders a text/URL as a standalone scalable vector SVG QR code with quiet zone."""
    matrix = generate_qr_matrix(text)
    size = len(matrix)
    total_size = size + 2 * border
    rects = []
    for r in range(size):
        for c in range(size):
            if matrix[r][c] == 1:
                rects.append(f"M{c + border},{r + border}h1v1h-1z")
    path_data = "".join(rects)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_size} {total_size}" width="{total_size * scale}" height="{total_size * scale}" shape-rendering="crispEdges">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <path fill="#000000" d="{path_data}"/>
</svg>"""
