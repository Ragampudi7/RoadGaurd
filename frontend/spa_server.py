"""Static server for dist/ with SPA fallback, so deep links like /app/reports work."""
import http.server, os, socketserver

ROOT = "/home/claude/frontend/dist"


class SPA(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path) and not os.path.exists(os.path.join(path, "index.html")):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, *a):
        pass


# Threading: the E2E opens three browser contexts at once and a single-threaded
# server makes the third one hang until the first goes idle.
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


with Server(("127.0.0.1", 5173), SPA) as httpd:
    httpd.serve_forever()
