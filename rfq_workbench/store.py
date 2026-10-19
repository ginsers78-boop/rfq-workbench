"""Local persistent review records, stable IDs and optimistic concurrency."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .extraction import ExtractionError


class ReviewedLine(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    id: str
    line_number: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=2000)
    specification: str | None = Field(max_length=4000)
    quantity: float | None = Field(ge=0)
    unit: str | None = Field(max_length=100)
    category: str
    source_quote: str = Field(min_length=1, max_length=4000)
    source_page: int | None = Field(default=None, ge=1, le=50)
    source_kind: Literal["extracted", "image_transcription"] = "extracted"
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    approved: bool
    excluded: bool = False
    exclusion_reason: str = Field(default="", max_length=1000)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    revision: int = Field(ge=1)
    lines: list[ReviewedLine] = Field(min_length=1, max_length=1000)
    source_verified: bool = False
    coverage_verified: bool = False


class Store:
    def __init__(self, path: Path, categories: list[dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.categories = {item["id"] for item in categories}
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS requirements (id TEXT PRIMARY KEY, created TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS requirement_history (requirement_id TEXT NOT NULL REFERENCES requirements(id) ON DELETE CASCADE, revision INTEGER NOT NULL, recorded TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(requirement_id, revision))")
            connection.execute("INSERT OR IGNORE INTO requirement_history SELECT id, revision, created, 'history_started_at_existing_revision', payload FROM requirements")
            connection.execute("CREATE TABLE IF NOT EXISTS suppliers (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL, email TEXT NOT NULL)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS supplier_email ON suppliers(lower(email))")
            connection.execute("CREATE TABLE IF NOT EXISTS rfqs (id TEXT PRIMARY KEY, requirement_id TEXT NOT NULL REFERENCES requirements(id) ON DELETE CASCADE, signature TEXT NOT NULL UNIQUE, payload TEXT NOT NULL, bundle BLOB NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS page_previews (requirement_id TEXT NOT NULL REFERENCES requirements(id) ON DELETE CASCADE, page INTEGER NOT NULL, image BLOB NOT NULL, PRIMARY KEY(requirement_id, page))")
            connection.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL, name TEXT NOT NULL, source BLOB, progress TEXT NOT NULL, result_id TEXT REFERENCES requirements(id) ON DELETE SET NULL, error TEXT)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute("PRAGMA secure_delete = ON")
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, document: dict, result: dict, *, connection=None, previews=None):
        identifier = str(uuid.uuid4())
        record = {"id": identifier, "created": datetime.now(timezone.utc).isoformat(), "revision": 1,
                  "status": "needs_review", "document": document, "analysis": result,
                  "lines": [{**line, "id": str(uuid.uuid4()), "approved": False} for line in result["extraction"]["lines"]]}
        # needs_review is diagnostic model output, never human approval.
        for line in record["lines"]:
            line.pop("needs_review", None)
        for line, location in zip(record["lines"], result.get("line_locations", [])):
            line.update(source_start=location["start"], source_end=location["end"])
        def persist(writer):
            writer.execute("INSERT INTO requirements VALUES (?, ?, ?, ?)", (identifier, record["created"], 1, json.dumps(record)))
            self.record_history(writer, record, "extracted")
            for page, image in previews or []:
                writer.execute("INSERT INTO page_previews VALUES (?, ?, ?)", (identifier, page, image))
        if connection is None:
            with self.connect() as writer:
                persist(writer)
        else:
            persist(connection)
        return record

    @staticmethod
    def record_history(connection, record, event):
        connection.execute("INSERT INTO requirement_history VALUES (?, ?, ?, ?, ?)", (record["id"], record["revision"], datetime.now(timezone.utc).isoformat(), event, json.dumps(record)))

    def history(self, identifier):
        self.get(identifier)
        with self.connect() as connection:
            rows = connection.execute("SELECT revision, recorded, event, payload FROM requirement_history WHERE requirement_id = ? ORDER BY revision", (identifier,)).fetchall()
        return [{"revision": row[0], "recorded": row[1], "event": row[2], "record": json.loads(row[3])} for row in rows]

    def get(self, identifier):
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM requirements WHERE id = ?", (identifier,)).fetchone()
        if not row:
            raise ExtractionError("The requirement was not found. It may have been deleted.")
        return json.loads(row[0])

    def list(self):
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM requirements ORDER BY created DESC LIMIT 100").fetchall()
        return [{key: record[key] for key in ("id", "created", "revision", "status")} | {"name": record["document"]["name"]}
                for row in rows for record in [json.loads(row[0])]]

    def review(self, identifier, payload):
        try:
            review = Review.model_validate(payload)
        except ValueError:
            raise ExtractionError("Review data is invalid. Check the line fields and numeric quantities.") from None
        record = self.get(identifier)
        originals = {line["id"]: line for line in record["lines"]}
        ids = [line.id for line in review.lines]
        if len(set(ids)) != len(ids) or not set(originals).issubset(ids):
            raise ExtractionError("The review must preserve every extracted line and its permanent ID.")
        for line in review.lines:
            original = originals.get(line.id)
            if original:
                if line.line_number != original["line_number"] or line.source_quote != original["source_quote"] or line.source_page != original.get("source_page") or line.source_kind != original.get("source_kind", "extracted") or line.source_start != original.get("source_start") or line.source_end != original.get("source_end"):
                    raise ExtractionError("Original line numbers and source quotations cannot be changed.")
            else:
                if line.source_start is not None or line.source_end is not None:
                    raise ExtractionError("Manual source offsets are assigned from the document, not accepted from the browser.")
                try:
                    uuid.UUID(line.id)
                except ValueError:
                    raise ExtractionError("New product lines require a valid permanent ID.") from None
                if not line.source_quote.strip():
                    raise ExtractionError("A manually added line needs an exact quotation from the original document.")
                if line.source_page is not None:
                    pages = {page["page"] for page in record["document"].get("page_details", []) if page["method"] == "local_vision"}
                    if line.source_page not in pages:
                        raise ExtractionError("Choose a saved OCR image page for manual image transcription.")
                    line.source_kind = "image_transcription"
                elif line.source_quote in record["document"]["text"]:
                    line.source_kind = "extracted"
                else:
                    raise ExtractionError("A manually added line needs an exact quotation, or an OCR image page and human transcription.")
            if line.category not in self.categories:
                raise ExtractionError("Choose a configured category.")
            if not line.description.strip():
                raise ExtractionError("Each line needs a product description.")
            if line.excluded and (line.approved or not line.exclusion_reason.strip()):
                raise ExtractionError("An excluded line needs a reason and cannot also be approved.")
            if line.approved and (line.quantity is None or line.quantity <= 0 or not line.unit or not line.unit.strip() or line.category == "Unclassified"):
                raise ExtractionError("To approve a line, enter a positive quantity, a unit and a classified category.")
        record["lines"] = [line.model_dump() for line in review.lines]
        record["source_verified"] = review.source_verified if record["document"].get("used_ocr") else True
        requires_coverage_review = len(record["analysis"].get("parts", [])) > 1 or any("source_start" in finding for finding in record["analysis"].get("validation_findings", []))
        record["coverage_verified"] = review.coverage_verified if requires_coverage_review else True
        record["status"] = "reviewed" if record["source_verified"] and record["coverage_verified"] and any(not line.excluded for line in review.lines) and all(line.approved or line.excluded for line in review.lines) else "needs_review"
        record["revision"] = review.revision + 1
        with self.connect() as connection:
            changed = connection.execute("UPDATE requirements SET payload = ?, revision = ? WHERE id = ? AND revision = ?",
                                         (json.dumps(record), record["revision"], identifier, review.revision)).rowcount
            if changed != 1:
                raise ExtractionError("This requirement changed in another tab. Reopen it before saving your review.")
            self.record_history(connection, record, "review_saved")
        return record

    def delete(self, identifier):
        with self.connect() as connection:
            changed = connection.execute("DELETE FROM requirements WHERE id = ?", (identifier,)).rowcount
        if not changed:
            raise ExtractionError("The requirement was not found.")
