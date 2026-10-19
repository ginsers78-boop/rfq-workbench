"""Durable single-worker processing queue with recovery and cooperative cancellation."""
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .errors import ExtractionError, ProcessingCancelled as Cancelled
from .extraction import extract, annotate_pages
from .ocr_documents import read_with_ocr
from .readers import MAX_BYTES


def now():
    return datetime.now(timezone.utc).isoformat()


class Jobs:
    def __init__(self, store, categories, inference_lock):
        self.store, self.categories, self.inference_lock = store, categories, inference_lock
        self.stopped = threading.Event()
        self.wake = threading.Event()
        with store.connect() as connection:
            connection.execute("UPDATE jobs SET status='queued', progress='Resuming after server restart', updated=? WHERE status='running'", (now(),))
        self.thread = threading.Thread(target=self.run, daemon=True, name="rfq-local-processing")

    def start(self):
        self.thread.start()
        self.wake.set()

    def stop(self):
        self.stopped.set()
        self.wake.set()

    def create(self, name, content, consent):
        if consent is not True:
            raise ExtractionError("Confirm local temporary upload storage and any persistent OCR page previews before background processing.")
        if not isinstance(name, str) or not 1 <= len(name) <= 255 or not content or len(content) > MAX_BYTES:
            raise ExtractionError("Select a nonempty document up to 10 MB.")
        if Path(name).suffix.casefold() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".docx", ".xlsx"}:
            raise ExtractionError("Background processing accepts PDF, TXT, DOCX, XLSX, PNG, JPEG and non-animated WebP.")
        identifier, timestamp = str(uuid.uuid4()), now()
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if count >= 3:
                raise ExtractionError("Three documents are already queued. Wait for completion or cancel one before uploading another.")
            connection.execute("INSERT INTO jobs VALUES (?, 'queued', ?, ?, ?, ?, 'Waiting for local processing', NULL, NULL)", (identifier, timestamp, timestamp, Path(name).name, content))
        self.wake.set()
        return self.get(identifier)

    def get(self, identifier):
        with self.store.connect() as connection:
            row = connection.execute("SELECT id,status,created,updated,name,progress,result_id,error FROM jobs WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise ExtractionError("The processing task was not found.")
        return dict(zip(["id", "status", "created", "updated", "name", "progress", "result_id", "error"], row))

    def list(self):
        with self.store.connect() as connection:
            rows = connection.execute("SELECT id FROM jobs ORDER BY created DESC LIMIT 20").fetchall()
        return [self.get(row[0]) for row in rows]

    def cancel(self, identifier):
        with self.store.connect() as connection:
            count = connection.execute("UPDATE jobs SET status='cancelled',source=NULL,progress='Cancelled; any current model call must finish before the next task',updated=? WHERE id=? AND status IN ('queued','running')", (now(), identifier)).rowcount
        if not count:
            raise ExtractionError("The task already finished or was not found.")
        self.wake.set()
        return self.get(identifier)

    def progress(self, identifier, message):
        if self.stopped.is_set():
            raise Cancelled()
        with self.store.connect() as connection:
            changed = connection.execute("UPDATE jobs SET progress=?,updated=? WHERE id=? AND status='running'", (message, now(), identifier)).rowcount
        if not changed:
            raise Cancelled()

    def process(self, identifier, name, content):
        try:
            document, previews = read_with_ocr(name, content, lambda message: self.progress(identifier, message))
            self.progress(identifier, "Extracting product lines from the complete document text")
            result = extract(document["text"], self.categories, progress=lambda message: self.progress(identifier, message))
            self.progress(identifier, "Saving the validated result and review images")
            annotate_pages(result, document)
            with self.store.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                state = connection.execute("SELECT status FROM jobs WHERE id=?", (identifier,)).fetchone()
                if not state or state[0] != "running" or self.stopped.is_set():
                    raise Cancelled()
                record = self.store.create(document, result, connection=connection, previews=previews)
                connection.execute("UPDATE jobs SET status='completed',source=NULL,result_id=?,progress='Completed; human review required',updated=? WHERE id=?", (record["id"], now(), identifier))
        except Cancelled:
            # Cancelled tasks remain cancelled. A running task on shutdown retains its
            # source so the next application instance can genuinely reprocess it.
            return
        except Exception as error:
            if self.stopped.is_set():
                return
            if not isinstance(error, ExtractionError):
                logging.exception("Background document processing failed")
            message = str(error) if isinstance(error, ExtractionError) else "Processing failed. No partial requirement was saved. Check the local server."
            with self.store.connect() as connection:
                connection.execute("UPDATE jobs SET status='failed',source=NULL,error=?,progress='Failed; no partial requirement saved',updated=? WHERE id=? AND status='running'", (message, now(), identifier))

    def run(self):
        while not self.stopped.is_set():
            with self.store.connect() as connection:
                row = connection.execute("SELECT id,name,source FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
            if not row:
                self.wake.wait(1)
                self.wake.clear()
                continue
            if not self.inference_lock.acquire(timeout=1):
                continue
            try:
                if self.stopped.is_set():
                    continue
                with self.store.connect() as connection:
                    changed = connection.execute("UPDATE jobs SET status='running',progress='Starting document reader',updated=? WHERE id=? AND status='queued'", (now(), row[0])).rowcount
                if changed and not self.stopped.is_set():
                    self.process(*row)
            finally:
                self.inference_lock.release()
