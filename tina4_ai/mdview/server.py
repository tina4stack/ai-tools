"""HTTP server for mdview — serves rendered Markdown with live reload."""

import json
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .files import list_entries, read_file, validate_path
from .viewer import build_html

ASSETS_DIR = Path(__file__).parent / "assets"
LOCK_FILE = Path.home() / ".mdview.lock"


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class MdViewHandler(BaseHTTPRequestHandler):
    """Request handler for the mdview server."""

    project_root: Path
    initial_path: str
    nav_listeners: list  # shared list of (queue) SSE clients

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

        content_types = {".js": "application/javascript", ".css": "text/css"}
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
        elif path == "/api/navigate-events":
            self._handle_navigate_events()
        elif path.startswith("/assets/"):
            self._send_asset(path[8:])
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/open":
            self._handle_open()
        else:
            self.send_error(404)

    def _handle_index(self):
        self._send_html(build_html(self.initial_path))

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
        self._send_json({"entries": entries, "current_path": req_path, "md_count": total_md})

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

    def _handle_open(self):
        """POST /api/open — navigate all open browser tabs to a file."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            file_path = data.get("path", "")
        except (json.JSONDecodeError, AttributeError):
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        # Broadcast to all SSE listeners
        event = f"data: {json.dumps({'path': file_path})}\n\n".encode()
        dead = []
        for q in self.nav_listeners:
            try:
                q.append(event)
            except Exception:
                dead.append(q)
        for q in dead:
            try:
                self.nav_listeners.remove(q)
            except ValueError:
                pass

        self._send_json({"ok": True, "listeners": len(self.nav_listeners)})

    def _handle_navigate_events(self):
        """SSE endpoint — pushes navigate events to the browser."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        queue = []
        self.nav_listeners.append(queue)
        try:
            while True:
                if queue:
                    self.wfile.write(queue.pop(0))
                    self.wfile.flush()
                else:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            try:
                self.nav_listeners.remove(queue)
            except ValueError:
                pass

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
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _read_lock() -> int | None:
    """Return the port from the lock file, or None if not running."""
    try:
        port = int(LOCK_FILE.read_text().strip())
        # Verify it's actually alive
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return port
    except Exception:
        return None


def _write_lock(port: int):
    LOCK_FILE.write_text(str(port))


def _remove_lock():
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


def _send_open(port: int, file_path: str):
    """Tell the running instance to navigate to file_path."""
    body = json.dumps({"path": file_path}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/open",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2):
        pass


def main():
    """CLI entry point for mdview."""
    args = sys.argv[1:]

    # Version flag
    if args and args[0] in ("--version", "-v"):
        from tina4_ai import __version__
        print(f"mdview {__version__}")
        return

    # Determine target
    if args:
        target = Path(args[0]).resolve()
    else:
        target = Path.cwd()

    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        sys.exit(1)

    # Figure out project root and relative file path
    if target.is_file():
        project_root = target.parent
        initial_path = target.name
    else:
        project_root = target
        initial_path = ""

    # Singleton check — reuse existing instance if running
    running_port = _read_lock()
    if running_port:
        try:
            rel = str(target.relative_to(project_root)) if target.is_file() else ""
            _send_open(running_port, rel or initial_path)
            webbrowser.open(f"http://127.0.0.1:{running_port}")
            print(f"mdview already running — opened in existing instance (port {running_port})")
            return
        except Exception:
            # Stale lock — fall through and start fresh
            _remove_lock()

    port = int(os.environ.get("PORT", 0)) or _find_free_port()
    nav_listeners: list = []

    handler = type("Handler", (MdViewHandler,), {
        "project_root": project_root,
        "initial_path": initial_path,
        "nav_listeners": nav_listeners,
    })

    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    _write_lock(port)

    url = f"http://127.0.0.1:{port}"
    print(f"mdview serving {project_root}")
    print(f"Open: {url}")
    print("Press Ctrl+C to stop")

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    def shutdown(signum, frame):
        print("\nShutting down...")
        _remove_lock()
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        server.serve_forever()
    finally:
        _remove_lock()


if __name__ == "__main__":
    main()
