"""Single-user loopback application. Not a public or multi-tenant server."""
from __future__ import annotations

import base64
import binascii
import json
import logging
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .extraction import ExtractionError, extract, response_schema, annotate_pages
from .chunks import plan_parts
from .readers import read_document, validate_text
from .store import Store
from .privacy import suggested_markers
from .suppliers import list_suppliers, save_supplier
from .rfq import approve_rfq, create_rfq, current_rfq, download_rfq, save_privacy
from .jobs import Jobs
from .instance_lock import InstanceLock

ROOT = Path(__file__).resolve().parent.parent
MAX_REQUEST = 14 * 1024 * 1024


def make_server(port: int = 8765, database: Path | None = None) -> ThreadingHTTPServer:
    categories = json.loads((ROOT / "categories.json").read_text(encoding="utf-8"))
    response_schema(categories)
    database = database or ROOT / "data" / "workbench.sqlite3"
    instance_lock = InstanceLock(database)
    store = Store(database, categories)
    token = secrets.token_urlsafe(32)
    inference_lock = threading.Lock()
    jobs = Jobs(store, categories, inference_lock)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            # Document names, contents and query strings are intentionally not logged.
            logging.info("%s %s", self.command, args[1] if len(args) > 1 else "request")

        def reply(self, status, data, content_type="application/json; charset=utf-8", filename=None):
            try:
                self.send_reply(status, data, content_type, filename)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # A tab refresh/close is a disconnected transport, not a backend failure.
                # Never attempt a second HTTP response on that closed connection.
                self.close_connection = True

        def send_reply(self, status, data, content_type="application/json; charset=utf-8", filename=None):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8") if content_type.startswith("application/json") else data
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def allowed_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.allowed_host():
                self.reply(403, {"error": "Open this app using its printed 127.0.0.1 address."})
                return
            path = urlsplit(self.path).path
            try:
                if path == "/api/config":
                    self.reply(200, {"token": token, "categories": categories})
                elif path == "/api/requirements":
                    self.reply(200, store.list())
                elif path == "/api/suppliers":
                    self.reply(200, list_suppliers(store))
                elif path == "/api/jobs":
                    self.reply(200, jobs.list())
                elif path.startswith("/api/jobs/"):
                    parts = path.strip("/").split("/")
                    if len(parts) != 3:
                        raise ExtractionError("The processing task path is invalid.")
                    self.reply(200, jobs.get(parts[2]))
                elif path.startswith("/api/rfqs/"):
                    parts = path.strip("/").split("/")
                    if len(parts) == 3:
                        with store.connect() as connection:
                            result, _ = current_rfq(connection, parts[2])
                        self.reply(200, result)
                    elif len(parts) == 4 and parts[3] == "download":
                        self.reply(200, download_rfq(store, parts[2]), "application/zip", "rfq-preparation-package.zip")
                    else:
                        self.reply(404, {"error": "Page not found."})
                elif path.startswith("/api/requirements/"):
                    parts = path.strip("/").split("/")
                    if len(parts) == 3:
                        self.reply(200, store.get(parts[2]))
                    elif len(parts) == 4 and parts[3] == "export":
                        self.reply(200, store.get(parts[2]), filename="requirement-review.json")
                    elif len(parts) == 4 and parts[3] == "history":
                        self.reply(200, store.history(parts[2]))
                    elif len(parts) == 5 and parts[3] == "pages":
                        if not parts[4].isdigit():
                            raise ExtractionError("The source page number is invalid.")
                        with store.connect() as connection:
                            row = connection.execute("SELECT image FROM page_previews WHERE requirement_id=? AND page=?", (parts[2], int(parts[4]))).fetchone()
                        if not row:
                            raise ExtractionError("The source page preview was not found.")
                        self.reply(200, row[0], "image/jpeg")
                    elif len(parts) == 4 and parts[3] == "privacy":
                        record = store.get(parts[2])
                        self.reply(200, record.get("privacy", {"markers": suggested_markers(record["document"]["text"]), "confirmed": False}))
                    elif len(parts) == 4 and parts[3] == "rfqs":
                        store.get(parts[2])
                        with store.connect() as connection:
                            rows = connection.execute("SELECT payload FROM rfqs WHERE requirement_id = ? ORDER BY rowid DESC", (parts[2],)).fetchall()
                        self.reply(200, [{key: record[key] for key in ("id", "revision", "created", "status")} for row in rows for record in [json.loads(row[0])]])
                    else:
                        self.reply(404, {"error": "Page not found."})
                elif path in {"/", "/app.js", "/jobs.js", "/procurement.js", "/style.css", "/procurement.css"}:
                    name = "index.html" if path == "/" else path[1:]
                    mime = "text/javascript; charset=utf-8" if name.endswith(".js") else "text/css; charset=utf-8" if name.endswith(".css") else "text/html; charset=utf-8"
                    self.reply(200, (ROOT / "web" / name).read_bytes(), mime)
                else:
                    self.reply(404, {"error": "Page not found."})
            except ExtractionError as error:
                self.reply(404, {"error": str(error)})
            except Exception:
                logging.exception("Local read failed")
                self.reply(500, {"error": "The local record could not be read. Check the server terminal."})

        def do_POST(self):
            if not self.allowed_host() or self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}" or not secrets.compare_digest(self.headers.get("X-Workbench-Token", ""), token):
                self.close_connection = True
                self.reply(403, {"error": "The request could not be verified. Reload the local application."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_REQUEST:
                    self.close_connection = True
                    self.reply(413, {"error": "The request exceeds the upload limit or has no body."})
                    return
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ExtractionError("Expected a JSON request.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ExtractionError("Expected a JSON object.")
                path = urlsplit(self.path).path
                if path == "/api/jobs":
                    upload = payload.get("file")
                    if not isinstance(upload, dict) or not isinstance(upload.get("name"), str) or not isinstance(upload.get("base64"), str):
                        raise ExtractionError("The file upload is malformed.")
                    self.reply(202, jobs.create(upload["name"], base64.b64decode(upload["base64"], validate=True), payload.get("local_storage_consent")))
                elif path.startswith("/api/jobs/"):
                    parts = path.strip("/").split("/")
                    if len(parts) == 4 and parts[3] == "cancel":
                        self.reply(200, jobs.cancel(parts[2]))
                    else:
                        self.reply(404, {"error": "Action not found."})
                elif path == "/api/analyze":
                    if "file" in payload:
                        upload = payload["file"]
                        if not isinstance(upload, dict) or not isinstance(upload.get("name"), str) or not 1 <= len(upload["name"]) <= 255 or not isinstance(upload.get("base64"), str):
                            raise ExtractionError("The file upload is malformed.")
                        document = read_document(upload["name"], base64.b64decode(upload["base64"], validate=True))
                    else:
                        source = validate_text(payload.get("text"))
                        document = {"name": "Pasted requirement", "size": len(source.encode("utf-8")), "pages": None, "text": source}
                    if len(plan_parts(document["text"])) > 1:
                        raise ExtractionError("This document needs multiple model parts. Enable background processing and local storage in the upload form, then submit again.")
                    if not inference_lock.acquire(blocking=False):
                        self.reply(409, {"error": "Another local extraction is running. Wait for it to finish."})
                        return
                    try:
                        result = annotate_pages(extract(document["text"], categories), document)
                        record = store.create(document, result)
                    finally:
                        inference_lock.release()
                    self.reply(201, record)
                elif path == "/api/suppliers":
                    self.reply(200, save_supplier(store, payload))
                elif path.startswith("/api/rfqs/"):
                    parts = path.strip("/").split("/")
                    if len(parts) == 4 and parts[3] == "approve" and payload.get("confirmed") is True:
                        self.reply(200, approve_rfq(store, parts[2]))
                    else:
                        raise ExtractionError("Confirm that you reviewed the exact RFQ preview before approving it.")
                elif path.startswith("/api/requirements/"):
                    parts = path.strip("/").split("/")
                    if len(parts) == 4 and parts[3] == "review":
                        self.reply(200, store.review(parts[2], payload))
                    elif len(parts) == 4 and parts[3] == "privacy":
                        self.reply(200, save_privacy(store, parts[2], payload))
                    elif len(parts) == 4 and parts[3] == "rfqs":
                        self.reply(201, create_rfq(store, parts[2], payload))
                    elif len(parts) == 4 and parts[3] == "delete":
                        store.delete(parts[2])
                        self.reply(200, {"deleted": True})
                    else:
                        self.reply(404, {"error": "Action not found."})
                else:
                    self.reply(404, {"error": "Action not found."})
            except (ExtractionError, ValueError, TypeError, binascii.Error) as error:
                message = str(error) if isinstance(error, ExtractionError) else "The request contains invalid data."
                self.reply(400, {"error": message})
            except Exception:
                logging.exception("Local operation failed")
                self.reply(500, {"error": "The operation failed. Your saved records remain available; check the server terminal."})

    class WorkbenchServer(ThreadingHTTPServer):
        def server_close(self):
            jobs.stop()
            if jobs.thread.is_alive():
                jobs.thread.join(timeout=2)
            super().server_close()
            instance_lock.close()
    try:
        server = WorkbenchServer(("127.0.0.1", port), Handler)
    except Exception:
        instance_lock.close()
        raise
    server.daemon_threads = True
    jobs.start()
    return server


def serve(port=8765, database=None):
    server = make_server(port, database)
    print(f"RFQ Workbench: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Local single-user mode. Database: {database or ROOT / 'data' / 'workbench.sqlite3'}. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
