import unittest

from rfq_workbench.extraction import ExtractionError, equivalent_quantity, evaluate, response_schema


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.labels = [{"line_number": "1", "quantity": 120, "unit": "pcs", "category": "Fasteners"}]

    def test_correct_fields_pass(self):
        self.assertEqual(evaluate(self.labels, self.labels)["exact_line_accuracy"], 1)

    def test_wrong_units_are_visible(self):
        output = evaluate(self.labels, [{**self.labels[0], "unit": None}])
        self.assertEqual(output["exact_line_accuracy"], 0)
        self.assertEqual(output["findings"][0]["field"], "unit")

    def test_missing_lines_are_not_ignored(self):
        self.assertEqual(evaluate(self.labels, [])["findings"][0]["issue"], "missing_line")

    def test_invented_lines_reduce_score(self):
        actual = self.labels + [{**self.labels[0], "line_number": "2"}]
        self.assertEqual(evaluate(self.labels, actual)["exact_line_accuracy"], 0.5)

    def test_duplicate_numbers_are_rejected(self):
        with self.assertRaises(ExtractionError):
            evaluate(self.labels, self.labels * 2)

    def test_empty_labels_are_rejected(self):
        with self.assertRaises(ExtractionError):
            evaluate([], [])

    def test_quantity_comparison_does_not_guess_missing_values(self):
        self.assertTrue(equivalent_quantity(120, "120.0"))
        self.assertFalse(equivalent_quantity(None, 0))
        self.assertFalse(equivalent_quantity("NaN", "NaN"))

    def test_category_enum_is_the_configured_list(self):
        schema = response_schema([{"id": "A", "description": "A category"}])
        self.assertEqual(schema["properties"]["lines"]["items"]["properties"]["category"]["enum"], ["A"])

    def test_duplicate_categories_are_rejected(self):
        with self.assertRaises(ExtractionError):
            response_schema([{"id": "A"}, {"id": "A"}])


if __name__ == "__main__":
    unittest.main()
