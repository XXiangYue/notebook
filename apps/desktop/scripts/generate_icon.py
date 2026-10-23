from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
ICONSET_DIR = BUILD_DIR / "icon.iconset"


def clamp(value: float) -> int:
    return max(0, min(255, round(value)))


def mix(
    a: tuple[int, int, int, int], b: tuple[int, int, int, int], t: float
) -> tuple[int, int, int, int]:
    return tuple(clamp(a[i] * (1 - t) + b[i] * t) for i in range(4))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return 1.0 if value >= edge1 else 0.0
    x = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return x * x * (3 - 2 * x)


def rounded_rect_alpha(
    x: float, y: float, left: float, top: float, right: float, bottom: float, radius: float
) -> float:
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    distance = math.hypot(x - cx, y - cy)
    return 1.0 - smoothstep(radius - 1.4, radius + 1.4, distance)


def line_alpha(
    px: float, py: float, ax: float, ay: float, bx: float, by: float, width: float
) -> float:
    vx = bx - ax
    vy = by - ay
    wx = px - ax
    wy = py - ay
    length_squared = vx * vx + vy * vy
    if length_squared == 0:
        distance = math.hypot(px - ax, py - ay)
    else:
        t = max(0.0, min(1.0, (wx * vx + wy * vy) / length_squared))
        distance = math.hypot(px - (ax + t * vx), py - (ay + t * vy))
    return 1.0 - smoothstep(width / 2 - 1.0, width / 2 + 1.0, distance)


def composite(
    dst: tuple[int, int, int, int], src: tuple[int, int, int, int], alpha: float
) -> tuple[int, int, int, int]:
    src_alpha = (src[3] / 255.0) * alpha
    dst_alpha = dst[3] / 255.0
    out_alpha = src_alpha + dst_alpha * (1 - src_alpha)
    if out_alpha == 0:
        return (0, 0, 0, 0)
    channels = []
    for index in range(3):
        value = (src[index] * src_alpha + dst[index] * dst_alpha * (1 - src_alpha)) / out_alpha
        channels.append(clamp(value))
    channels.append(clamp(out_alpha * 255))
    return tuple(channels)


def encode_png(
    path: Path, width: int, height: int, pixels: list[tuple[int, int, int, int]]
) -> None:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        row_start = y * width
        for r, g, b, a in pixels[row_start : row_start + width]:
            raw.extend((r, g, b, a))

    def chunk(name: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )

    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


def render_icon(size: int) -> list[tuple[int, int, int, int]]:
    scale = size / 1024
    pixels: list[tuple[int, int, int, int]] = []

    for y in range(size):
        for x in range(size):
            px = (x + 0.5) / scale
            py = (y + 0.5) / scale

            color = (0, 0, 0, 0)

            shadow = rounded_rect_alpha(px, py - 22, 78, 86, 946, 962, 218)
            color = composite(color, (20, 24, 28, 58), shadow * 0.52)

            base_alpha = rounded_rect_alpha(px, py, 78, 62, 946, 930, 218)
            base_top = (38, 113, 107, 255)
            base_bottom = (24, 46, 69, 255)
            base = mix(base_top, base_bottom, py / 1024)
            color = composite(color, base, base_alpha)

            glow = max(0.0, 1 - math.hypot(px - 326, py - 254) / 520)
            color = composite(color, (116, 210, 177, 88), base_alpha * glow)

            page_shadow = rounded_rect_alpha(px, py, 230, 216, 818, 812, 52)
            color = composite(color, (0, 0, 0, 50), page_shadow * 0.5)

            page = rounded_rect_alpha(px, py, 214, 190, 802, 786, 52)
            page_color = mix((255, 253, 246, 255), (232, 235, 224, 255), py / 1024)
            color = composite(color, page_color, page)

            fold = rounded_rect_alpha(px, py, 690, 190, 802, 304, 34)
            if px + py > 992:
                color = composite(color, (208, 218, 208, 255), fold * 0.9)

            spine = rounded_rect_alpha(px, py, 198, 178, 308, 800, 42)
            color = composite(color, (31, 88, 82, 255), spine)
            color = composite(
                color, (112, 215, 176, 210), line_alpha(px, py, 276, 242, 276, 736, 10)
            )

            for offset in (0, 112, 224, 336):
                alpha = rounded_rect_alpha(px, py, 360, 306 + offset, 700, 352 + offset, 17)
                color = composite(color, (82, 105, 105, 115), alpha)

            nib = rounded_rect_alpha(px, py, 528, 514, 716, 650, 34)
            color = composite(color, (252, 184, 82, 255), nib)
            color = composite(
                color, (190, 102, 54, 255), line_alpha(px, py, 546, 618, 696, 532, 22)
            )

            spark = line_alpha(px, py, 698, 346, 778, 346, 12)
            spark = max(spark, line_alpha(px, py, 738, 306, 738, 386, 12))
            color = composite(color, (255, 243, 164, 230), spark)

            pixels.append(color)

    return pixels


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }

    for filename, size in outputs.items():
        encode_png(ICONSET_DIR / filename, size, size, render_icon(size))

    encode_png(BUILD_DIR / "icon.png", 1024, 1024, render_icon(1024))


if __name__ == "__main__":
    main()
