"""HTTP server for mdview — serves rendered Markdown with live reload."""

import json
import os
import signal
import socket
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .files import list_entries, read_file, validate_path
from .viewer import build_html

ASSETS_DIR = Path(__file__).parent / "assets"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MdViewHandler(BaseHTTPRequestHandler):
    """Request handler for the mdview server."""

    project_root: Path
    initial_path: str

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_asset(self, name: str):
        path = ASSETS_DIR / name
        if not path.is_file():
            self.send_error(404)
            return

        content_types = {
            ".js": "application/javascript",
            ".css": "text/css",
        }
        ct = content_types.get(path.suffix, "application/octet-stream")
        body = path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/":
            self._handle_index()
        elif path == "/api/files":
            self._handle_files(params)
        elif path == "/api/content":
            self._handle_content(params)
        elif path == "/api/watch":
            self._handle_watch(params)
        elif path.startswith("/assets/"):
            self._send_asset(path[8:])
        else:
            self.send_error(404)

    def _handle_index(self):
        html = build_html(self.initial_path)
        self._send_html(html)

    def _handle_files(self, params: dict):
        req_path = params.get("path", ["."])[0]
        target = validate_path(req_path, self.project_root)

        if target is None:
            self._send_json({"error": "Invalid path"}, 403)
            return

        if not target.is_dir():
            self._send_json({"error": "Not a directory"}, 400)
            return

        entries = list_entries(target, self.project_root)
        total_md = sum(e.get("md_count", 1) for e in entries)

        self._send_json({
            "entries": entries,
            "current_path": req_path,
            "md_count": total_md,
        })

    def _handle_content(self, params: dict):
        req_path = params.get("path", [None])[0]
        if not req_path:
            self._send_json({"error": "Missing path parameter"}, 400)
            return

        target = validate_path(req_path, self.project_root)
        if target is None:
            self._send_json({"error": "Invalid path"}, 403)
            return

        result = read_file(target, self.project_root)
        if result is None:
            self._send_json({"error": "File not found or not readable"}, 404)
            return

        self._send_json(result)

    def _handle_watch(self, params: dict):
        """SSE endpoint — polls file mtime and sends 'changed' events."""
        req_path = params.get("path", [None])[0]
        if not req_path:
            self.send_error(400)
            return

        target = validate_path(req_path, self.project_root)
        if target is None or not target.is_file():
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_mtime = target.stat().st_mtime
        try:
            while True:
                time.sleep(1)
                try:
                    current_mtime = target.stat().st_mtime
                except OSError:
                    break
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    self.wfile.write(b"data: changed\n\n")
                    self.wfile.flush()
                else:
                    # Keep-alive
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    """CLI entry point for mdview."""
    args = sys.argv[1:]

    # Determine target
    if args:
        target = Path(args[0]).resolve()
    else:
        target = Path.cwd()

    # Figure out project root and initial file
    if target.is_file():
        project_root = target.parent
        initial_path = target.name
    elif target.is_dir():
        project_root = target
        initial_path = ""
    else:
        print(f"Error: {target} does not exist", file=sys.stderr)
        sys.exit(1)

    port = int(os.environ.get("PORT", 0)) or _find_free_port()

    # Create handler class with project context
    handler = type("Handler", (MdViewHandler,), {
        "project_root": project_root,
        "initial_path": initial_path,
    })

    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}"

    print(f"mdview serving {project_root}")
    print(f"Open: {url}")
    print("Press Ctrl+C to stop")

    # Open browser after a short delay
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    # Handle graceful shutdown
    def shutdown(signum, frame):
        print("\nShutting down...")
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.serve_forever()


if __name__ == "__main__":
    main()
