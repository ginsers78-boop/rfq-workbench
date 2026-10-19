import base64
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from rfq_workbench.server import MAX_REQUEST, make_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.server = make_server(0, Path(self.directory.name) / "app.sqlite3")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        status, config, _ = self.call("GET", "/api/config")
        self.assertEqual(status, 200)
        self.token = config["token"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def call(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = json.dumps(data) if data is not None else None
        supplied = {"Content-Type": "application/json"}
        if hasattr(self, "token"):
            supplied.update({"Origin": self.origin, "X-Workbench-Token": self.token})
        supplied.update(headers or {})
        try:
            connection.request(method, path, body=body, headers=supplied)
            response = connection.getresponse()
            raw = response.read()
            payload = json.loads(raw) if response.getheader("Content-Type").startswith("application/json") else raw
            return response.status, payload, dict(response.getheaders())
        finally:
            connection.close()

    def test_same_origin_security(self):
        for header in [{"X-Workbench-Token": "wrong"}, {"Origin": "https://untrusted.example"}, {"Host": "untrusted.example"}]:
            with self.subTest(header=header):
                self.assertEqual(self.call("POST", "/api/analyze", {"text": "test"}, header)[0], 403)
        self.assertEqual(self.call("GET", "/api/config", headers={"Host": "untrusted.example"})[0], 403)

    def test_malformed_and_oversized_input(self):
        for data in [[], {"text": " "}, {"text": 123}, {"file": {"name": "x.txt", "base64": "???"}}, {"file": "not an object"}]:
            with self.subTest(data=data):
                self.assertEqual(self.call("POST", "/api/analyze", data)[0], 400)
        self.assertEqual(self.call("POST", "/api/analyze", {}, {"Content-Length": str(MAX_REQUEST + 1)})[0], 413)

    def test_real_reader_errors_and_missing_record(self):
        for name, content in [("empty.txt", b" "), ("bad.pdf", b"not PDF"), ("run.exe", b"program")]:
            self.assertEqual(self.call("POST", "/api/analyze", {"file": {"name": name, "base64": base64.b64encode(content).decode()}})[0], 400)
        self.assertEqual(self.call("GET", "/api/requirements/missing")[0], 404)
        self.assertEqual(self.call("POST", "/api/requirements/missing/delete", {})[0], 400)

    def test_assets_security_headers_and_no_path_traversal(self):
        for path in ["/", "/app.js", "/style.css"]:
            status, _, headers = self.call("GET", path)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ["/../categories.json", "/data/workbench.sqlite3", "/.git/config"]:
            self.assertEqual(self.call("GET", path)[0], 404)
