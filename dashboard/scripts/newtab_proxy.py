#!/usr/bin/env python3
"""Reverse proxy that opens the Top-tab pub map preview in a new tab.

DAC 0.21 escapes raw HTML in text widgets, so the markdown image link cannot
carry target=_blank. Caddy keeps reverse_proxying 127.0.0.1:8321. This process
listens there, forwards to DAC on 8322, and injects pub_map/newtab.js into
HTML responses. The script sets target=_blank and rel=noopener only on the
preview image link.

Static /pub_map and /scorecards paths are served from dashboard/ when a
request reaches this process directly (local checks). Production Caddy still
serves those paths itself and only proxies the dashboard.
"""

from __future__ import annotations

import argparse
import http.client
import select
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1]
SCRIPT_PATH = DASHBOARD / "pub_map" / "newtab.js"
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
MIME = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}


def inject_newtab(body: bytes, script: bytes) -> bytes:
    """Insert the preview-link script before the last </body>."""
    if b"pub-map-newtab" in body:
        return body
    idx = body.lower().rfind(b"</body>")
    if idx < 0:
        return body
    tag = b"<script>/* pub-map-newtab */" + script + b"</script>"
    return body[:idx] + tag + body[idx:]


def static_path(dashboard: Path, url_path: str) -> Path | None:
    """Map a Caddy-style static URL onto a file under dashboard/, or None."""
    path = url_path.split("?", 1)[0]
    if path == "/pub_map.html":
        return dashboard / "pub_map.html"
    if path == "/scorecards" or path == "/scorecards/":
        return dashboard / "scorecards" / "index.html"
    if path.startswith("/pub_map/"):
        return _under(dashboard / "pub_map", path[len("/pub_map/") :])
    if path.startswith("/scorecards/"):
        return _under(dashboard / "scorecards", path[len("/scorecards/") :])
    return None


def _under(root: Path, rel: str) -> Path | None:
    if rel == "" or rel.endswith("/"):
        rel = rel + "index.html"
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


class NewtabProxy(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, listen: tuple[str, int], upstream: tuple[str, int], dashboard: Path, script: bytes):
        self.upstream_host, self.upstream_port = upstream
        self.dashboard = dashboard
        self.script = script
        super().__init__(listen, ProxyHandler)


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: NewtabProxy

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch()

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        if (self.headers.get("Upgrade") or "").lower() == "websocket":
            self._tunnel()
            return
        target = static_path(self.server.dashboard, self.path)
        if target is not None and self.command in ("GET", "HEAD"):
            self._serve_file(target)
            return
        self._proxy()

    def _serve_file(self, path: Path) -> None:
        data = path.read_bytes()
        ctype = MIME.get(path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP
        }
        headers["Accept-Encoding"] = "identity"
        conn = http.client.HTTPConnection(
            self.server.upstream_host,
            self.server.upstream_port,
            timeout=60,
        )
        try:
            conn.request(self.command, self.path, body=body if length else None, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            ctype = resp.getheader("Content-Type") or ""
            if self.command != "HEAD" and "text/html" in ctype.lower():
                data = inject_newtab(data, self.server.script)
            self.send_response(resp.status)
            for key, value in resp.getheaders():
                if key.lower() in HOP_BY_HOP or key.lower() == "content-length":
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        finally:
            conn.close()

    def _tunnel(self) -> None:
        upstream = socket.create_connection(
            (self.server.upstream_host, self.server.upstream_port),
            timeout=10,
        )
        request = f"{self.command} {self.path} HTTP/1.1\r\n"
        request += "".join(f"{key}: {value}\r\n" for key, value in self.headers.items())
        request += "\r\n"
        upstream.sendall(request.encode("iso-8859-1"))
        upstream.setblocking(False)
        self.connection.setblocking(False)
        sockets = [self.connection, upstream]
        try:
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    break
                for sock in readable:
                    other = upstream if sock is self.connection else self.connection
                    try:
                        chunk = sock.recv(65536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        return
                    other.sendall(chunk)
        finally:
            upstream.close()
            self.close_connection = True


def parse_host(value: str) -> tuple[str, int]:
    host, _, port = value.rpartition(":")
    if not host:
        raise SystemExit(f"expected host:port, got {value}")
    return host, int(port)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen", default="127.0.0.1:8321")
    parser.add_argument("--upstream", default="127.0.0.1:8322")
    parser.add_argument("--dashboard", default=str(DASHBOARD))
    args = parser.parse_args()
    script = Path(args.dashboard, "pub_map", "newtab.js").read_bytes()
    server = NewtabProxy(parse_host(args.listen), parse_host(args.upstream), Path(args.dashboard), script)
    host, port = server.server_address[:2]
    print(f"newtab proxy on {host}:{port} -> {args.upstream}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
