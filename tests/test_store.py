import copy
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from rfq_workbench.extraction import ExtractionError
from rfq_workbench.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "review.sqlite3"
        self.categories = [{"id": "Fasteners"}, {"id": "Unclassified"}]
        self.store = Store(self.path, self.categories)
        self.record = self.store.create({"name": "test.txt", "text": "1. Bolt 12 pcs\n2. Nut 8 pcs"}, {
            "extraction": {"lines": [{"line_number": "1", "description": "Bolt", "specification": None, "quantity": 12,
                "unit": "pcs", "category": "Fasteners", "source_quote": "1. Bolt 12 pcs", "needs_review": True}]}})

    def tearDown(self):
        self.directory.cleanup()

    def payload(self):
        return {"revision": self.record["revision"], "lines": copy.deepcopy(self.record["lines"])}

    def test_persistence_and_approval(self):
        payload = self.payload()
        payload["lines"][0]["approved"] = True
        saved = self.store.review(self.record["id"], payload)
        restored = Store(self.path, self.categories).get(self.record["id"])
        self.assertEqual(saved, restored)
        self.assertEqual(restored["status"], "reviewed")
        self.assertEqual(restored["revision"], 2)
        self.assertEqual(restored["lines"][0]["id"], self.record["lines"][0]["id"])

    def test_stale_save_rejected(self):
        self.store.review(self.record["id"], self.payload())
        with self.assertRaisesRegex(ExtractionError, "another tab"):
            self.store.review(self.record["id"], self.payload())

    def test_missing_fields_cannot_be_approved(self):
        for field, value in [("quantity", None), ("quantity", 0), ("quantity", float("nan")), ("unit", " "), ("category", "Unclassified"), ("category", "invented"), ("description", " ")]:
            payload = self.payload()
            payload["lines"][0].update({field: value, "approved": True})
            with self.subTest(field=field, value=value), self.assertRaises(ExtractionError):
                self.store.review(self.record["id"], payload)

    def test_identity_and_source_are_immutable(self):
        for field, value in [("id", str(uuid.uuid4())), ("line_number", "99"), ("source_quote", "made up")]:
            payload = self.payload()
            payload["lines"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ExtractionError):
                self.store.review(self.record["id"], payload)

    def test_add_missed_line_with_real_provenance(self):
        payload = self.payload()
        line = copy.deepcopy(payload["lines"][0])
        line.update(id=str(uuid.uuid4()), line_number="2", description="Nut", quantity=8, source_quote="2. Nut 8 pcs")
        payload["lines"].append(line)
        saved = self.store.review(self.record["id"], payload)
        self.assertEqual(len(saved["lines"]), 2)
        self.assertEqual(saved["analysis"], self.record["analysis"])

    def test_cannot_invent_manual_source_or_drop_lines(self):
        payload = self.payload()
        line = copy.deepcopy(payload["lines"][0])
        line.update(id=str(uuid.uuid4()), line_number="2", source_quote="not in document")
        payload["lines"].append(line)
        with self.assertRaisesRegex(ExtractionError, "exact quotation"):
            self.store.review(self.record["id"], payload)
        with self.assertRaises(ExtractionError):
            self.store.review(self.record["id"], {"revision": 1, "lines": []})

    def test_delete(self):
        self.store.delete(self.record["id"])
        self.assertEqual(self.store.list(), [])
        with self.assertRaises(ExtractionError):
            self.store.get(self.record["id"])
