"""Crash/restart a test-owned server and genuinely resume a stored OCR upload."""
import base64
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

root = Path(__file__).resolve().parent.parent
database = root / "data" / f"qa-restart-{uuid.uuid4().hex}.sqlite3"
base = "http://127.0.0.1:8771"
log = (root / "data" / "queue-restart.log").open("w", encoding="utf-8")
child = None


def call(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers.update({"Origin": base, "X-Workbench-Token": token})
    request = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def start():
    process = subprocess.Popen([sys.executable, "-m", "rfq_workbench", "serve", "--port", "8771", "--database", str(database)], cwd=root, stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("The owned test server failed to start; inspect data/queue-restart.log.")
        try:
            config = call("/api/config")
            return process, config["token"]
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    process.terminate()
    process.wait(timeout=10)
    raise RuntimeError("The owned test server did not become ready.")


try:
    # Refuse an occupied test port; never stop or operate someone else's server.
    try:
        call("/api/config")
    except urllib.error.URLError:
        pass
    else:
        raise RuntimeError("Port 8771 is already occupied. Stop the test without touching that process.")
    child, token = start()
    content = (root / "data" / "ocr-inputs" / "mixed.pdf").read_bytes()
    job = call("/api/jobs", {"file": {"name": "mixed.pdf", "base64": base64.b64encode(content).decode()}, "local_storage_consent": True}, token)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = call("/api/jobs/" + job["id"])
        if state["status"] == "running":
            break
        time.sleep(0.1)
    assert state["status"] == "running", state
    child.terminate()  # Simulate interruption of this specific test-owned process.
    child.wait(timeout=10)
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT status,source FROM jobs WHERE id=?", (job["id"],)).fetchone()
    assert row[0] == "running" and row[1] == content
    print("Interrupted a running job; exact upload bytes survived.", flush=True)
    child, token = start()
    deadline = time.monotonic() + 600
    previous = ""
    while time.monotonic() < deadline:
        state = call("/api/jobs/" + job["id"])
        if state["progress"] != previous:
            print(state["progress"], flush=True)
            previous = state["progress"]
        if state["status"] not in {"queued", "running"}:
            break
        time.sleep(1)
    assert state["status"] == "completed", state
    record = call("/api/requirements/" + state["result_id"])
    assert len(record["lines"]) == 3
    assert record["document"]["used_ocr"] is True
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM requirements").fetchone()[0] == 1
        assert connection.execute("SELECT source FROM jobs WHERE id=?", (job["id"],)).fetchone()[0] is None
    call("/api/requirements/" + record["id"] + "/delete", {}, token)
    report = {"passed": True, "actual_process_interrupted": True, "exact_upload_recovered": True, "completed_after_restart": True, "requirements_created": 1, "raw_upload_purged": True}
    (root / "data" / "queue-restart-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
finally:
    if child and child.poll() is None:
        child.terminate()
        child.wait(timeout=10)
    log.close()
