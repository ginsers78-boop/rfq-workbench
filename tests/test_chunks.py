import copy
import tempfile
import unittest
from pathlib import Path

from rfq_workbench.chunks import MAX_DOCUMENT_TEXT, MAX_PART_BYTES, locate_lines, plan_parts, source_sections
from rfq_workbench.errors import ExtractionError
from rfq_workbench.extraction import annotate_pages
from rfq_workbench.readers import validate_text
from rfq_workbench.store import Store


class ChunkTests(unittest.TestCase):
    def test_sheet_headers_are_separate_from_previous_product(self):
        source = "Sheet: A\nLine | Description | Quantity | Unit\n1 | Bolt | 12 | pcs\nSheet: B\nLine | Unit | Quantity | Description\n1 | m | 8 | Cable\n"
        sections = source_sections(source)
        rows = [source[section.start:section.end] for section in sections if section.number]
        self.assertEqual(rows, ["1 | Bolt | 12 | pcs\n", "1 | m | 8 | Cable\n"])
        self.assertEqual("".join(source[section.start:section.end] for section in sections), source)

    def test_lossless_coverage_utf8_and_whitespace(self):
        source = "Customer: Fictional supplier test\r\n\r\n" + "".join(f"{number}. Болт M10x50, {number} pcs\r\n    Grade: A2-70; thread tolerance 6g.\r\n\r\n" for number in range(1, 100))
        parts = plan_parts(source)
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(source[part[0].start:part[-1].end] for part in parts), source)
        for part in parts:
            self.assertLessEqual(len(source[part[0].start:part[-1].end].encode("utf-8")), MAX_PART_BYTES)
            self.assertLessEqual(sum(section.number is not None for section in part), 8)
            for section in part:
                if section.number:
                    self.assertIn("tolerance 6g", source[section.start:section.end])

    def test_old_limit_removed_and_real_limit_enforced(self):
        self.assertEqual(len(validate_text("Ж" * 9000)), 9000)
        with self.assertRaisesRegex(ExtractionError, "1 MiB"):
            validate_text("a" * (MAX_DOCUMENT_TEXT + 1))

    def test_oversized_single_record_is_not_cut(self):
        with self.assertRaisesRegex(ExtractionError, "cannot be split safely"):
            plan_parts("1. " + "a" * MAX_PART_BYTES)

    def test_empty_and_oversized_documents(self):
        for text in ["", " ", "a" * (MAX_DOCUMENT_TEXT + 1)]:
            with self.subTest(length=len(text)), self.assertRaises(ExtractionError):
                plan_parts(text)

    def test_duplicate_numbers_preserve_distinct_source_locations(self):
        source = "1. Bolt 12 pcs\n\nPage two\n1. Nut 8 pcs\n"
        lines = [{"line_number": "1", "source_quote": "1. Bolt 12 pcs"}, {"line_number": "1", "source_quote": "1. Nut 8 pcs"}]
        locations = locate_lines(source, lines, source_sections(source), require_exact=True)
        self.assertEqual(locations[0]["start"], 0)
        self.assertGreater(locations[1]["start"], locations[0]["end"])
        result = {"line_locations": locations}
        annotate_pages(result, {"page_details": [{"page":1,"start":0,"end":16},{"page":2,"start":16,"end":len(source)}]})
        self.assertEqual(result["line_pages"][str(locations[1]["start"])], [2])

    def test_identical_real_rows_are_not_deduplicated(self):
        source = "1. Bolt 12 pcs\n1. Bolt 12 pcs\n"
        line = {"line_number": "1", "source_quote": "1. Bolt 12 pcs"}
        locations = locate_lines(source, [line, line], source_sections(source), require_exact=True)
        self.assertNotEqual(locations[0]["start"], locations[1]["start"])
        with self.assertRaisesRegex(ExtractionError, "uniquely anchored"):
            locate_lines(source, [line, line, line], source_sections(source), require_exact=True)

    def test_a_quote_from_another_part_cannot_be_merged(self):
        source = "1. Bolt 12 pcs\n2. Nut 8 pcs\n"
        with self.assertRaises(ExtractionError):
            locate_lines(source, [{"line_number":"2","source_quote":"2. Nut 8 pcs"}], source_sections(source)[:1], require_exact=True)

    def test_model_cannot_change_original_number(self):
        source = "001. Bolt 12 pcs\n"
        with self.assertRaisesRegex(ExtractionError,"changed an original"):
            locate_lines(source,[{"line_number":"1","source_quote":"Bolt 12 pcs"}],source_sections(source),require_exact=True)

    def test_non_product_paragraph_parts_have_no_missing_characters(self):
        source = ("Contract terms: delivery inspection and packing details.\n\n" * 500)
        parts = plan_parts(source)
        self.assertGreater(len(parts),1)
        self.assertEqual("".join(source[part[0].start:part[-1].end] for part in parts), source)

    def test_repeated_numbers_survive_review_with_immutable_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "review.sqlite3", [{"id":"Fasteners"}])
            source = "1. Bolt 12 pcs\n1. Nut 8 pcs"
            lines = [{"line_number":"1","description":name,"specification":None,"quantity":qty,"unit":"pcs","category":"Fasteners","source_quote":quote,"needs_review":True} for name,qty,quote in [("Bolt",12,"1. Bolt 12 pcs"),("Nut",8,"1. Nut 8 pcs")]]
            locations=locate_lines(source,lines,source_sections(source),require_exact=True)
            record=store.create({"name":"repeat.txt","text":source},{"extraction":{"lines":lines},"line_locations":locations})
            edited=copy.deepcopy(record["lines"])
            for line in edited:
                line["approved"]=True
            saved=store.review(record["id"],{"revision":1,"lines":edited})
            self.assertEqual(saved["status"],"reviewed")
            self.assertNotEqual(saved["lines"][0]["id"],saved["lines"][1]["id"])
            edited[0]["source_start"]=10
            with self.assertRaisesRegex(ExtractionError,"cannot be changed"):
                store.review(record["id"],{"revision":2,"lines":edited})

    def test_multipart_needs_full_document_review(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)/"review.sqlite3",[{"id":"Fasteners"}])
            line={"line_number":"1","description":"Bolt","specification":None,"quantity":12,"unit":"pcs","category":"Fasteners","source_quote":"1. Bolt 12 pcs","needs_review":True}
            record=store.create({"name":"long.txt","text":"1. Bolt 12 pcs"},{"extraction":{"lines":[line]},"parts":[{"part":"1/2"},{"part":"2/2"}]})
            lines=record["lines"]
            lines[0]["approved"]=True
            record=store.review(record["id"],{"revision":1,"lines":lines})
            self.assertEqual(record["status"],"needs_review")
            record=store.review(record["id"],{"revision":2,"lines":lines,"coverage_verified":True})
            self.assertEqual(record["status"],"reviewed")
