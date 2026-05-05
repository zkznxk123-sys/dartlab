"""POC 서버 — OAuth 콜백을 index.html로 리다이렉트."""
import http.server


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # /auth/callback?code=xxx → /?code=xxx 로 리다이렉트
        if self.path.startswith("/auth/callback"):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            self.send_response(302)
            self.send_header("Location", f"/?{query}")
            self.end_headers()
        else:
            super().do_GET()

if __name__ == "__main__":
    s = http.server.HTTPServer(("localhost", 1455), Handler)
    print("POC 서버: http://localhost:1455/")
    s.serve_forever()
