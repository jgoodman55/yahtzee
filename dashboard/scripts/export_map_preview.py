#!/usr/bin/env python3
"""Refresh the Top-tab pub-map preview.

Screenshots the real Boroughs view, crops a wide banner (coloured boroughs,
no header and no zoom control), and writes a compressed JPEG.

This is optional. Run it on a machine with Chrome when pubs or boroughs
change. The droplet rebuild does not call it.

    python3 dashboard/scripts/export_map_preview.py

Writes dashboard/pub_map/preview.jpg (served in production as
/pub_map/preview.jpg).
"""

from __future__ import annotations

import argparse
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
DASHBOARD = REPO / "dashboard"
OUT = DASHBOARD / "pub_map" / "preview.jpg"
# Wide banner. A full-width desktop card is about 1300px; this stays
# near a tile-row height there, and the file is ~2x so a phone stays sharp.
ASPECT = 5.5  # width / height. About a tile-row tall on a desktop card.
MAX_BYTES = 200_000
CHROME = "/usr/bin/google-chrome"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LABEL = "Pub map"


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
            top = Math.min(top, r.top);
            bottom = Math.max(bottom, r.bottom);
            left = Math.min(left, r.left);
            right = Math.max(right, r.right);
          }
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


def _frame_boroughs(page) -> dict:
    """Zoom and pan so the played boroughs fill a wide banner.

    The default Greater London frame leaves the colours as a small cluster.
    A few zoom-in clicks, then a pan, puts that cluster across the banner.
    Chrome stays up until the zoom control has been clicked.
    """
    view = page.viewport_size
    target_w = view["width"] * 0.75
    for _ in range(4):
        box = _played_box(page)
        if box["w"] >= target_w:
            break
        page.click(".leaflet-control-zoom-in")
        page.wait_for_timeout(300)
    for _ in range(2):
        box = _played_box(page)
        dx = view["width"] / 2 - box["cx"]
        dy = view["height"] / 2 - box["cy"]
        if abs(dx) < 12 and abs(dy) < 12:
            break
        page.mouse.move(view["width"] / 2, view["height"] / 2)
        page.mouse.down()
        page.mouse.move(view["width"] / 2 + dx, view["height"] / 2 + dy, steps=12)
        page.mouse.up()
        page.wait_for_timeout(250)
    page.add_style_tag(
        content="""
        .chrome, .leaflet-control-zoom, .leaflet-control-attribution,
        .legend, .leaflet-tooltip, .borough-label, .leaflet-popup {
          display: none !important;
        }
        """
    )
    page.wait_for_timeout(700)
    box = _played_box(page)
    width = view["width"]
    height = width / ASPECT
    y = box["cy"] - height / 2
    y = max(0, min(y, view["height"] - height))
    return {"x": 0, "y": y, "width": width, "height": height}


def _label(image: Image.Image) -> Image.Image:
    """Small corner chip so the banner reads as tappable. No headline."""
    img = image.convert("RGB")
    draw = ImageDraw.Draw(img)
    # ~13px on a 1x desktop banner; the file is about 2x that width.
    # About 10px on a 390px phone, still a corner chip on a desktop card.
    size = max(22, round(img.width * 10 / 390))
    font = ImageFont.truetype(FONT, size)
    pad_x = int(size * 0.7)
    pad_y = int(size * 0.38)
    text = LABEL
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top
    margin = int(size * 0.85)
    x0 = margin
    y0 = img.height - margin - th - pad_y * 2
    x1 = x0 + tw + pad_x * 2
    y1 = y0 + th + pad_y * 2
    radius = int(size * 0.45)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(18, 23, 31))
    draw.text((x0 + pad_x, y0 + pad_y - top), text, font=font, fill=(243, 246, 250))
    return img


def _save(image: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    quality = 78
    while quality >= 50:
        image.save(dest, format="JPEG", quality=quality, optimize=True, progressive=True)
        if dest.stat().st_size <= MAX_BYTES:
            return
        quality -= 4
    # Still over the budget: shrink, then compress again.
    scale = 0.85
    current = image
    while dest.stat().st_size > MAX_BYTES and current.width > 1200:
        current = current.resize(
            (int(current.width * scale), int(current.height * scale)),
            Image.Resampling.LANCZOS,
        )
        current.save(dest, format="JPEG", quality=60, optimize=True, progressive=True)
    if dest.stat().st_size > MAX_BYTES:
        raise SystemExit(f"{dest} is {dest.stat().st_size} bytes, over {MAX_BYTES}")


def capture(url: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_function(
            """() => document.querySelector('#btn-boroughs')?.getAttribute('aria-pressed') === 'true'
              && document.querySelectorAll('#map path[fill-opacity="0.78"]').length >= 7
              && document.querySelectorAll('.leaflet-tile-loaded').length > 4"""
        )
        page.wait_for_timeout(400)
        clip = _frame_boroughs(page)
        png = page.screenshot(clip=clip, type="png")
        browser.close()

    image = Image.open(__import__("io").BytesIO(png))
    _save(_label(image), OUT)
    print(f"wrote {OUT.relative_to(REPO)} {image.size[0]}x{image.size[1]} {OUT.stat().st_size} bytes")


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
