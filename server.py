"""
Self-contained Web Server & REST API for Handwriting Machine & Handcode Studio.
Uses Python's standard library http.server (no external web framework dependencies).
"""

import os
import sys
import json
import mimetypes
import tempfile
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Ensure engine is in path
sys.path.insert(0, os.path.dirname(__file__))

from engine.extractor import extract_text
from engine.paginator import TEMPLATES, paginate_and_render
from engine.gcode import generate_gcode
from engine.streamer import streamer_instance

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class HandcodeHandler(BaseHTTPRequestHandler):
    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/templates":
            self.send_json({"success": True, "templates": TEMPLATES})
            return

        elif path == "/api/stream/status":
            self.send_json({"success": True, "status": streamer_instance.get_status()})
            return

        elif path == "/api/ports":
            self.send_json({"success": True, "ports": streamer_instance.list_ports()})
            return

        # Serve static files
        if path == "/" or path == "":
            rel_path = "index.html"
        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):]
        else:
            rel_path = path.lstrip("/")

        file_path = os.path.join(STATIC_DIR, rel_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or "application/octet-stream"
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        try:
            if path == "/api/extract":
                # Handle file upload for extraction
                if "boundary=" in content_type:
                    boundary = content_type.split("boundary=")[1].strip().encode()
                    raw_data = self.rfile.read(content_length)
                    parts = raw_data.split(b"--" + boundary)
                    filename = "upload.tmp"
                    file_bytes = b""
                    
                    for part in parts:
                        if b"Content-Disposition:" in part and b"filename=" in part:
                            header_end = part.find(b"\r\n\r\n")
                            if header_end != -1:
                                headers_part = part[:header_end].decode("utf-8", errors="replace")
                                for line in headers_part.splitlines():
                                    if "filename=" in line:
                                        raw_fn = line.split("filename=")[1].strip('"\'; ')
                                        filename = os.path.basename(raw_fn)
                                file_bytes = part[header_end + 4:].rstrip(b"\r\n")
                                break
                    
                    if not file_bytes:
                        self.send_json({"success": False, "error": "No file content detected"}, 400)
                        return

                    suffix = os.path.splitext(filename)[1] or ".png"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_f:
                        tmp_f.write(file_bytes)
                        tmp_path = tmp_f.name

                    try:
                        extracted = extract_text(tmp_path)
                        self.send_json({"success": True, "filename": filename, "text": extracted})
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                else:
                    self.send_json({"success": False, "error": "Expected multipart/form-data"}, 400)
                return

            # Read JSON body for other POST endpoints
            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}

            if path == "/api/render":
                text = body.get("text", "")
                template_id = body.get("template_id", "kokuyo_camlin_small")
                custom_tpl = body.get("custom_template")

                if custom_tpl:
                    template = custom_tpl
                else:
                    template = TEMPLATES.get(template_id, TEMPLATES["kokuyo_camlin_small"])

                style = int(body.get("style", 1))
                bias = float(body.get("bias", 0.75))
                font_size = float(body.get("font_size", template.get("font_size", 5.2)))
                word_spacing = float(body.get("word_spacing", template.get("word_spacing", 3.2)))
                line_spacing = float(body.get("line_spacing", template.get("line_spacing", 8.0)))

                pages = paginate_and_render(
                    text=text,
                    template=template,
                    style=style,
                    bias=bias,
                    font_size=font_size,
                    word_spacing=word_spacing,
                    line_spacing=line_spacing
                )
                self.send_json({"success": True, "pages": pages, "total_pages": len(pages)})
                return

            elif path == "/api/gcode":
                pages = body.get("pages", [])
                page_index = body.get("page_index")
                pen_mode = body.get("pen_mode", "servo")
                pen_down_cmd = body.get("pen_down_cmd", "M5")
                pen_up_cmd = body.get("pen_up_cmd", "M3 S90")
                feed_draw = int(body.get("feed_draw", 1800))
                feed_travel = int(body.get("feed_travel", 5000))
                invert_y = bool(body.get("invert_y", False))
                flip_lab_record = bool(body.get("flip_lab_record", False))
                servo_delay_ms = int(body.get("servo_delay_ms", 150))
                return_to_origin = bool(body.get("return_to_origin", False))
                resume_from_current = body.get("resume_from_current")

                gcode_str = generate_gcode(
                    pages=pages,
                    page_index=page_index,
                    pen_mode=pen_mode,
                    pen_down_cmd=pen_down_cmd,
                    pen_up_cmd=pen_up_cmd,
                    feed_draw=feed_draw,
                    feed_travel=feed_travel,
                    invert_y=invert_y,
                    flip_lab_record=flip_lab_record,
                    servo_delay_ms=servo_delay_ms,
                    return_to_origin=return_to_origin,
                    resume_from_current=resume_from_current
                )
                self.send_json({"success": True, "gcode": gcode_str})
                return

            elif path == "/api/stream/start":
                gcode_str = body.get("gcode", "")
                port = body.get("port", "/dev/ttyUSB0")
                streamer_instance.port = port
                ok = streamer_instance.start_stream(gcode_str)
                self.send_json({"success": ok, "message": "Streaming started" if ok else "Failed to start streaming"})
                return

            elif path == "/api/stream/pause":
                streamer_instance.pause()
                self.send_json({"success": True})
                return

            elif path == "/api/stream/resume":
                streamer_instance.resume()
                self.send_json({"success": True})
                return

            elif path == "/api/stream/stop":
                streamer_instance.stop()
                self.send_json({"success": True})
                return

            elif path == "/api/machine/jog":
                dx = float(body.get("dx", 0.0))
                dy = float(body.get("dy", 0.0))
                feed = int(body.get("feed", 1500))
                ok = streamer_instance.jog(dx, dy, feed)
                self.send_json({"success": ok, "status": streamer_instance.get_status()})
                return

            elif path == "/api/machine/moveto":
                x = float(body.get("x", 0.0))
                y = float(body.get("y", 0.0))
                feed = int(body.get("feed", 3500))
                ok = streamer_instance.move_to(x, y, feed)
                self.send_json({"success": ok, "status": streamer_instance.get_status()})
                return

            elif path == "/api/machine/pen":
                down = bool(body.get("down", False))
                if "pen_down_cmd" in body and body["pen_down_cmd"]:
                    streamer_instance.pen_down_cmd = str(body["pen_down_cmd"]).strip()
                if "pen_up_cmd" in body and body["pen_up_cmd"]:
                    streamer_instance.pen_up_cmd = str(body["pen_up_cmd"]).strip()
                ok = streamer_instance.pen_test(down)
                self.send_json({"success": ok, "status": streamer_instance.get_status()})
                return

            elif path == "/api/machine/zero":
                ok = streamer_instance.set_zero()
                self.send_json({"success": ok, "status": streamer_instance.get_status()})
                return

            elif path == "/api/machine/unlock":
                ok = streamer_instance.unlock()
                self.send_json({"success": ok, "status": streamer_instance.get_status()})
                return

            else:
                self.send_json({"success": False, "error": f"Unknown endpoint {path}"}, 404)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json({"success": False, "error": str(e)}, 500)


def run_server(port: int = 8080):
    server = ThreadedHTTPServer(("0.0.0.0", port), HandcodeHandler)
    print(f"Handcode Studio server running at http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(p)
