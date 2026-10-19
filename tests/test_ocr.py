import io
import tempfile
import copy
import uuid
import threading
import unittest
from pathlib import Path

from PIL import Image
from reportlab.pdfgen import canvas

from rfq_workbench.errors import ExtractionError, ProcessingCancelled
from rfq_workbench.instance_lock import InstanceLock
from rfq_workbench.jobs import Jobs
from rfq_workbench.ocr import normalise_image
from rfq_workbench.ocr_documents import read_with_ocr, render_page
from rfq_workbench.store import Store


class OCRTests(unittest.TestCase):
    def test_image_normalisation_pixels_transparency_and_metadata(self):
        image = Image.new("RGBA", (3000, 1000), (0, 0, 0, 0))
        data = io.BytesIO()
        image.save(data, "PNG")
        result = normalise_image(data.getvalue())
        with Image.open(io.BytesIO(result)) as prepared:
            self.assertEqual(prepared.format, "JPEG")
            self.assertEqual(prepared.mode, "RGB")
            self.assertLessEqual(max(prepared.size), 2200)
            self.assertEqual(prepared.getpixel((0, 0)), (255, 255, 255))
            self.assertFalse(prepared.getexif())

    def test_corrupted_and_animated_images(self):
        with self.assertRaises(ExtractionError):
            normalise_image(b"not an image")
        output = io.BytesIO()
        Image.new("RGB", (20, 20), "white").save(output, "WEBP", save_all=True, append_images=[Image.new("RGB", (20, 20), "black")], duration=100)
        with self.assertRaisesRegex(ExtractionError, "single-frame"):
            normalise_image(output.getvalue())

    def test_real_pdf_render_and_text_only_read(self):
        output = io.BytesIO()
        document = canvas.Canvas(output)
        document.drawString(40, 780, "10. Brass valve 12 pcs")
        document.save()
        rendered = render_page(output.getvalue(), 0)
        with Image.open(io.BytesIO(rendered)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertGreater(image.width, 1000)
        progress = []
        read, previews = read_with_ocr("text.pdf", output.getvalue(), progress.append)
        self.assertIn("Brass valve", read["text"])
        self.assertFalse(read["used_ocr"])
        self.assertEqual(previews, [])
        page = read["page_details"][0]
        self.assertEqual(read["text"][page["start"]:page["end"]], read["text"])

    def test_image_extension_mismatch_before_model(self):
        output = io.BytesIO()
        Image.new("RGB", (20, 20)).save(output, "PNG")
        with self.assertRaisesRegex(ExtractionError, "extension"):
            read_with_ocr("wrong.jpg", output.getvalue(), [].append)

    def test_cancellation_is_not_a_reader_failure(self):
        def cancel(message):
            raise ProcessingCancelled()
        output = io.BytesIO()
        Image.new("RGB", (20, 20)).save(output, "PNG")
        with self.assertRaises(ProcessingCancelled):
            read_with_ocr("x.png", output.getvalue(), cancel)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "test.sqlite3"
        self.categories = [{"id": "Fasteners"}, {"id": "Unclassified"}]
        self.store = Store(self.path, self.categories)
        # This queue is intentionally not started: exercise durable queue transitions
        # without substituting inference output or running an external model in unit tests.
        self.jobs = Jobs(self.store, self.categories, threading.Lock())

    def tearDown(self):
        self.jobs.stop()
        self.directory.cleanup()

    def test_consent_limits_and_cancel_purges_binary(self):
        with self.assertRaisesRegex(ExtractionError, "Confirm"):
            self.jobs.create("scan.pdf", b"content", False)
        job = self.jobs.create("scan.pdf", b"content", True)
        self.jobs.create("next.pdf", b"content", True)
        self.jobs.create("third.pdf", b"content", True)
        with self.assertRaisesRegex(ExtractionError, "Three"):
            self.jobs.create("fourth.pdf", b"content", True)
        self.assertEqual(self.jobs.cancel(job["id"])["status"], "cancelled")
        with self.store.connect() as connection:
            self.assertIsNone(connection.execute("SELECT source FROM jobs WHERE id=?", (job["id"],)).fetchone()[0])

    def test_recovery_preserves_original_bytes(self):
        job = self.jobs.create("scan.pdf", b"actual upload bytes", True)
        with self.store.connect() as connection:
            connection.execute("UPDATE jobs SET status='running' WHERE id=?", (job["id"],))
        recovered = Jobs(self.store, self.categories, threading.Lock())
        self.assertEqual(recovered.get(job["id"])["status"], "queued")
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT source FROM jobs WHERE id=?", (job["id"],)).fetchone()[0], b"actual upload bytes")
        recovered.stop()

    def test_actual_reader_failure_purges_source_and_saves_no_record(self):
        job = self.jobs.create("broken.pdf", b"not PDF", True)
        with self.store.connect() as connection:
            connection.execute("UPDATE jobs SET status='running' WHERE id=?", (job["id"],))
        self.jobs.process(job["id"], "broken.pdf", b"not PDF")
        self.assertEqual(self.jobs.get(job["id"])["status"], "failed")
        self.assertEqual(self.store.list(), [])
        with self.store.connect() as connection:
            self.assertIsNone(connection.execute("SELECT source FROM jobs WHERE id=?", (job["id"],)).fetchone()[0])

    def test_same_database_has_one_application_owner(self):
        first = InstanceLock(self.path)
        try:
            with self.assertRaisesRegex(ExtractionError, "another app"):
                InstanceLock(self.path)
        finally:
            first.close()
        reopened = InstanceLock(self.path)
        reopened.close()

    def test_ocr_preview_approval_and_delete_cascade(self):
        document = {"name": "scan.png", "text": "1. Bolt 12 pcs", "used_ocr": True, "page_details": [{"page": 1, "method": "local_vision"}]}
        analysis = {"extraction": {"lines": [{"line_number": "1", "description": "Bolt", "specification": None, "quantity": 12, "unit": "pcs", "category": "Fasteners", "source_quote": "1. Bolt 12 pcs", "needs_review": True}]}}
        image = normalise_image(self.image_bytes())
        record = self.store.create(document, analysis, previews=[(1, image)])
        lines = record["lines"]
        lines[0]["approved"] = True
        saved = self.store.review(record["id"], {"revision": 1, "lines": lines})
        self.assertEqual(saved["status"], "needs_review")
        saved = self.store.review(record["id"], {"revision": 2, "lines": lines, "source_verified": True})
        self.assertEqual(saved["status"], "reviewed")
        self.store.delete(record["id"])
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM page_previews").fetchone()[0], 0)

    def test_manual_image_transcription_preserves_ocr_and_provenance(self):
        document = {"name": "scan.png", "text": "1. Bolt 12 pcs", "used_ocr": True, "page_details": [{"page": 1, "method": "local_vision"}]}
        analysis = {"extraction": {"lines": [{"line_number": "1", "description": "Bolt", "specification": None, "quantity": 12, "unit": "pcs", "category": "Fasteners", "source_quote": "1. Bolt 12 pcs", "needs_review": True}]}}
        record = self.store.create(document, analysis, previews=[(1, normalise_image(self.image_bytes()))])
        lines = copy.deepcopy(record["lines"])
        manual = copy.deepcopy(lines[0])
        manual.update(id=str(uuid.uuid4()), line_number="2", description="Nut", source_quote="2. Nut 8 pcs", quantity=8, source_page=1, approved=True)
        lines[0]["approved"] = True
        lines.append(manual)
        saved = self.store.review(record["id"], {"revision": 1, "lines": lines, "source_verified": True})
        self.assertEqual(saved["lines"][1]["source_kind"], "image_transcription")
        self.assertEqual(saved["document"]["text"], "1. Bolt 12 pcs")
        self.assertEqual(saved["analysis"], analysis)
        self.assertEqual(saved["status"], "reviewed")
        forged = copy.deepcopy(saved["lines"])
        forged[1]["source_page"] = 2
        with self.assertRaisesRegex(ExtractionError, "cannot be changed"):
            self.store.review(record["id"], {"revision": 2, "lines": forged, "source_verified": True})
        missing = copy.deepcopy(lines)
        missing[1]["source_page"] = 2
        missing[1]["id"] = str(uuid.uuid4())
        with self.assertRaises(ExtractionError):
            self.store.review(record["id"], {"revision": 2, "lines": saved["lines"] + [missing[1]], "source_verified": True})

    @staticmethod
    def image_bytes():
        output = io.BytesIO()
        Image.new("RGB", (20, 20), "white").save(output, "PNG")
        return output.getvalue()
