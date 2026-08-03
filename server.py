import os
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

class FetchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/fetch":
            self.handle_fetch(parsed)
        else:
            self.handle_static(parsed)

    def handle_fetch(self, parsed):
        query = parse_qs(parsed.query)
        target_url = query.get("url", [None])[0]

        if not target_url:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing 'url' query parameter")
            return

        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; FetchServer/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content_type = response.headers.get("Content-Type", "text/plain")
                body = response.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"HTTP Error: {e.code} {e.reason}".encode())

        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"URL Error: {e.reason}".encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Server Error: {str(e)}".encode())

    def handle_static(self, parsed):
        path = parsed.path
        if path == "/":
            path = "/index.html"

        # Prevent path traversal
        safe_path = os.path.normpath(path).lstrip("/")
        file_path = os.path.join(STATIC_DIR, safe_path)

        if not file_path.startswith(STATIC_DIR) or not os.path.isfile(file_path):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        content_type, _ = mimetypes.guess_type(file_path)
        content_type = content_type or "application/octet-stream"

        with open(file_path, "rb") as f:
            body = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Keep Railway logs cleaner
        print(f"{self.address_string()} - {format % args}")

def run():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer((host, port), FetchHandler)
    print(f"Serving on {host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run()
