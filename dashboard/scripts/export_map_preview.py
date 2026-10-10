#!/usr/bin/env python3
"""Refresh the Top-tab pub-map preview.

Screenshots the real Boroughs view (no extra zoom), crops a banner that
contains every coloured borough plus the river, and writes:

  dashboard/pub_map/preview.jpg   clean map, no label, no seams
  dashboard/pub_map/preview.svg   that JPEG plus a corner chip

The chip is SVG text, not pixels in the JPEG, with a phone size that
cancels the downscale so it stays about 13px on a desktop card and on a
phone. DAC 0.21 escapes raw HTML in text widgets, so the chip cannot be a
separate DOM node.

This is optional. Run it on a machine with Chrome when pubs or boroughs
change. The droplet rebuild does not call it.

    python3 dashboard/scripts/export_map_preview.py
"""

from __future__ import annotations

import argparse
import base64
import io
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
DASHBOARD = REPO / "dashboard"
JPG_OUT = DASHBOARD / "pub_map" / "preview.jpg"
SVG_OUT = DASHBOARD / "pub_map" / "preview.svg"
# Desktop card is 1352px wide (1400px column minus padding). Height 560
# is the top of the requested desktop band, which makes a 358px phone
# image as tall as one shared aspect ratio allows (~148px).
DESK_W = 1352
DESK_H = 560
PHONE_W = 358
ASPECT = DESK_W / DESK_H
MAX_BYTES = 200_000
# JPEG is a bit wider than the desktop slot so a phone stays sharp.
JPG_W = 1800
CHROME = "/usr/bin/google-chrome"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LABEL = "Pub map"
CHIP_PX = 13
# Rendered image width. The SVG media query matches that, not the page.
PHONE_BREAK = 700


def _serve(port_holder: list[int]) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=str(DASHBOARD))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port_holder.append(httpd.server_address[1])
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def _played_box(page) -> dict:
    """Pixel box of boroughs that have visits (fill-opacity 0.78)."""
    box = page.evaluate(
        """() => {
          const paths = [...document.querySelectorAll('#map svg path')]
            .filter((p) => p.getAttribute('fill-opacity') === '0.78');
          if (!paths.length) return null;
          let top = Infinity, bottom = -Infinity, left = Infinity, right = -Infinity;
          for (const p of paths) {
            const r = p.getBoundingClientRect();
            if (r.width <= 0 || r.height <= 0) continue;
            top = Math.min(top, r.top);
            bottom = Math.max(bottom, r.bottom);
            left = Math.min(left, r.left);
            right = Math.max(right, r.right);
          }
          if (!Number.isFinite(top)) return null;
          return {
            top, bottom, left, right,
            w: right - left,
            h: bottom - top,
            cx: (left + right) / 2,
            cy: (top + bottom) / 2,
            n: paths.length,
          };
        }"""
    )
    if not box:
        raise SystemExit("no coloured boroughs on the map")
    return box


def _prepare(page) -> None:
    """Hide chrome and overlap tiles so the shot is one map, not a panel."""
    page.add_style_tag(
        content="""
        .chrome, .leaflet-control-zoom, .leaflet-control-attribution,
        .legend, .leaflet-tooltip, .borough-label, .leaflet-popup {
          display: none !important;
        }
        .leaflet-container { background: #e6e4e0 !important; }
        .leaflet-tile-container img.leaflet-tile {
          width: 257px !important;
          height: 257px !important;
        }
        """
    )


def _clip(box: dict, view_w: int, view_h: int, pad: int = 80) -> dict:
    """Wide frame around every played borough. No extra zoom."""
    bw = box["w"] + pad * 2
    bh = box["h"] + pad * 2
    if bw / bh < ASPECT:
        bw = bh * ASPECT
    else:
        bh = bw / ASPECT
    if bw > view_w or bh > view_h:
        scale = min(view_w / bw, view_h / bh)
        bw *= scale
        bh *= scale
    x = box["cx"] - bw / 2
    y = box["cy"] - bh / 2
    x = min(max(0.0, x), view_w - bw)
    y = min(max(0.0, y), view_h - bh)
    clip = {"x": x, "y": y, "width": bw, "height": bh}
    # The played boroughs themselves must stay inside the frame.
    if box["left"] < x - 1 or box["right"] > x + bw + 1 or box["top"] < y - 1 or box["bottom"] > y + bh + 1:
        raise SystemExit(f"crop clips played boroughs: box={box} clip={clip}")
    return clip


def _seam_columns(image: Image.Image) -> list[int]:
    """Columns that are a near-black vertical line through the map."""
    rgb = image.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    found: list[int] = []
    step = 2
    n = len(range(0, h, step))
    for x in range(1, w - 1):
        dark = 0
        for y in range(0, h, step):
            r, g, b = px[x, y]
            if r < 28 and g < 32 and b < 28:
                dark += 1
        if dark < 0.45 * n:
            continue
        # Neighbours should be map colours, not another dark feature.
        neighbor = 0
        for y in range(0, h, step * 4):
            for xx in (x - 1, x + 1):
                r, g, b = px[xx, y]
                if max(r, g, b) > 70:
                    neighbor += 1
        if neighbor > 4:
            found.append(x)
    return found


def _heal_seams(image: Image.Image) -> Image.Image:
    """Fill leftover tile gaps by copying the neighbouring column."""
    rgb = image.convert("RGB")
    px = rgb.load()
    w, _h = rgb.size
    cols = _seam_columns(rgb)
    if not cols:
        return rgb
    runs: list[tuple[int, int]] = []
    start = prev = cols[0]
    for x in cols[1:]:
        if x == prev + 1:
            prev = x
            continue
        runs.append((start, prev))
        start = prev = x
    runs.append((start, prev))
    for a, b in runs:
        left = a - 1
        right = b + 1
        if left < 0 or right >= w:
            continue
        for x in range(a, b + 1):
            for y in range(rgb.height):
                lr, lg, lb = px[left, y]
                rr, rg, rb = px[right, y]
                px[x, y] = ((lr + rr) // 2, (lg + rg) // 2, (lb + rb) // 2)
    return rgb


def _save_jpg(image: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    quality = 78
    while quality >= 50:
        image.save(dest, format="JPEG", quality=quality, optimize=True, progressive=True)
        if dest.stat().st_size <= MAX_BYTES:
            return
        quality -= 4
    raise SystemExit(f"{dest} is {dest.stat().st_size} bytes, over {MAX_BYTES}")


def _chip(class_name: str, font_px: float, view_w: int, view_h: int) -> str:
    """Bottom-left chip in viewBox units. font_px is chosen so it lands at ~13px."""
    size = max(10, round(font_px))
    font = ImageFont.truetype(FONT, size)
    # SVG <text y> is the baseline. Pillow's box is from the top of the em.
    ascent, descent = font.getmetrics()
    _l, _t, right, _b = ImageDraw.Draw(Image.new("RGB", (8, 8))).textbbox((0, 0), LABEL, font=font)
    tw = right - _l
    th = ascent + descent
    pad_x = round(size * 0.72)
    pad_y = round(size * 0.42)
    margin = round(size * 0.95)
    # A drawn chevron stays the same weight as the type. The → glyph
    # in this font shrinks to a speck at 13px.
    chev_h = max(6, round(ascent * 0.62))
    chev_w = max(4, round(chev_h * 0.62))
    gap = max(3, round(size * 0.28))
    stroke = max(1.6, size * 0.12)
    x = margin
    y = view_h - margin - (th + pad_y * 2)
    w = tw + gap + chev_w + pad_x * 2
    h = th + pad_y * 2
    rx = max(4, round(size * 0.42))
    text_x = x + pad_x - _l
    text_y = y + pad_y + ascent
    # Cap-height center, just to the right of the words.
    cx = text_x + tw + gap
    cy = text_y - ascent * 0.36
    path = (
        f"M {cx:.1f} {cy - chev_h / 2:.1f} "
        f"L {cx + chev_w:.1f} {cy:.1f} "
        f"L {cx:.1f} {cy + chev_h / 2:.1f}"
    )
    return (
        f'<g class="{class_name}" font-family="DejaVu Sans, sans-serif" '
        f'font-size="{size}" font-weight="700">'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="#12171F" fill-opacity="0.82"/>'
        f'<text x="{text_x:.1f}" y="{text_y:.1f}" fill="#F3F6FA">{LABEL}</text>'
        f'<path d="{path}" fill="none" stroke="#F3F6FA" stroke-width="{stroke:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f"</g>"
    )


def _write_svg(jpeg: Image.Image) -> None:
    raw = JPG_OUT.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    jw, jh = jpeg.size
    # Match the JPEG aspect so the browser does not letterbox the viewBox.
    disp_h = round(DESK_W * jh / jw)
    desk_font = CHIP_PX * jw / DESK_W
    phone_font = CHIP_PX * jw / PHONE_W
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{DESK_W}" height="{disp_h}" viewBox="0 0 {jw} {jh}">
  <style>
    .chip-phone {{ display: none; }}
    @media (max-width: {PHONE_BREAK}px) {{
      .chip-desk {{ display: none; }}
      .chip-phone {{ display: block; }}
    }}
  </style>
  <image href="data:image/jpeg;base64,{b64}" x="0" y="0" width="{jw}" height="{jh}" preserveAspectRatio="xMidYMid slice"/>
  {_chip("chip-desk", desk_font, jw, jh)}
  {_chip("chip-phone", phone_font, jw, jh)}
</svg>
'''
    SVG_OUT.write_text(svg)
    if SVG_OUT.stat().st_size > 400_000:
        raise SystemExit(f"{SVG_OUT} is {SVG_OUT.stat().st_size} bytes")


def capture(url: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        # Large frame at the map's own max zoom. device_scale_factor 1
        # avoids the black gaps a 2x screenshot leaves between tiles.
        view_w, view_h = 2600, 1700
        page = browser.new_page(
            viewport={"width": view_w, "height": view_h},
            device_scale_factor=1,
        )
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_function(
            """() => document.querySelector('#btn-boroughs')?.getAttribute('aria-pressed') === 'true'
              && document.querySelectorAll('#map path[fill-opacity="0.78"]').length >= 8
              && document.querySelectorAll('.leaflet-tile-loaded').length > 4"""
        )
        _prepare(page)
        page.wait_for_timeout(800)
        box = _played_box(page)
        if box["n"] < 8:
            raise SystemExit(f"expected 8 played boroughs, saw {box['n']}")
        clip = _clip(box, view_w, view_h)
        png = page.screenshot(clip=clip, type="png")
        browser.close()

    image = Image.open(io.BytesIO(png)).convert("RGB")
    image = _heal_seams(image)
    if _seam_columns(image):
        raise SystemExit(f"vertical seams remain at x={_seam_columns(image)[:8]}")
    image = image.resize((JPG_W, round(JPG_W / ASPECT)), Image.Resampling.LANCZOS)
    _save_jpg(image, JPG_OUT)
    saved = Image.open(JPG_OUT).convert("RGB")
    _write_svg(saved)
    print(
        f"wrote {JPG_OUT.relative_to(REPO)} {saved.size[0]}x{saved.size[1]} "
        f"{JPG_OUT.stat().st_size} bytes; "
        f"{SVG_OUT.relative_to(REPO)} {SVG_OUT.stat().st_size} bytes; "
        f"played {box['w']:.0f}x{box['h']:.0f} inside clip "
        f"{clip['width']:.0f}x{clip['height']:.0f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        help="Boroughs map page. Default: a temporary server rooted at dashboard/.",
    )
    args = parser.parse_args()
    if args.url:
        capture(args.url)
        return
    ports: list[int] = []
    httpd = _serve(ports)
    try:
        capture(f"http://127.0.0.1:{ports[0]}/pub_map.html")
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    main()
