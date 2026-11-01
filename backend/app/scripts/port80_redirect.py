import http.server
import socketserver
import sys

PORT = 80

class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        host = self.headers.get("Host", "10.77.222.155").split(":")[0]
        target = f"http://{host}:5173{self.path}"
        self.send_response(302)
        self.send_header("Location", target)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def log_message(self, format, *args):
        # Quiet logging
        pass

def main():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), RedirectHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()

