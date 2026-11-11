"""Local web page that runs the recipes. Listens on localhost only."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from canvaslib.runner import run_recipe
from recipes import discover

HOST = "127.0.0.1"
PORT = 3000
PUBLIC_DIR = Path(__file__).parent / "public"
INDEX_FILE = PUBLIC_DIR / "index.html"
# The only static files the server hands out. Anything else under /public stays private.
STATIC_FILES = {
    "/styles.css": (PUBLIC_DIR / "styles.css", "text/css; charset=utf-8"),
    "/app.js": (PUBLIC_DIR / "app.js", "text/javascript; charset=utf-8"),
}
RUN_PREFIX = "/api/run/"
RECIPES = {recipe["id"]: recipe for recipe in discover()}


def is_allowed_request(headers, port=PORT):
    """Reject requests from other websites (DNS rebinding and cross-site POSTs)."""
    allowed = {f"localhost:{port}", f"127.0.0.1:{port}"}
    if headers.get("Host") not in allowed:
        return False
    origin = headers.get("Origin")
    return origin is None or urlparse(origin).netloc in allowed


def public_view(recipe):
    return {key: recipe[key] for key in ("id", "title", "description", "writes", "source")}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self._allowed():
            return
        if self.path == "/":
            self._send(200, INDEX_FILE.read_bytes(), "text/html; charset=utf-8")
        elif self.path in STATIC_FILES:
            file, content_type = STATIC_FILES[self.path]
            self._send(200, file.read_bytes(), content_type)
        elif self.path == "/api/recipes":
            self._send_json(200, [public_view(r) for r in RECIPES.values()])
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self._allowed():
            return
        recipe = RECIPES.get(self.path.removeprefix(RUN_PREFIX))
        if not self.path.startswith(RUN_PREFIX) or recipe is None:
            self._send_json(404, {"error": "Unknown recipe"})
            return
        result, error = run_recipe(recipe["run"])
        if error:
            self._send_json(502, {"error": error})
        else:
            self._send_json(200, {"result": result})

    def _allowed(self):
        if is_allowed_request(self.headers):
            return True
        self._send_json(403, {"error": "Forbidden"})
        return False

    def _send_json(self, status, payload):
        self._send(status, json.dumps(payload).encode(), "application/json")

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Open http://localhost:{PORT} (Ctrl+C to stop)")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
