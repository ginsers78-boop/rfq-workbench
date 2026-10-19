import unittest
from rfq_workbench.source_facts import literal_quantity
from rfq_workbench.table_context import header_before, table_headers


class SourceFactTests(unittest.TestCase):
    def test_literal_values_are_read_not_generated(self):
        self.assertEqual(literal_quantity("1. Bolt M10x50, grade A2-70, 120 pcs.")["quantity"],120)
        self.assertEqual(literal_quantity("2. Cable 2.5mm2, 350 m.")["unit"],"m")
        self.assertEqual(literal_quantity("3 | cable | 2.75 | kg")["quantity"],2.75)

    def test_dimensions_and_ambiguity_are_not_guessed(self):
        for source in ["1. Bolt M10x50, quantity TBC", "2. Wire 2.5mm2", "3. Pipe length 200 m", "4. Bolt, 1,200 pcs", "5. Bolt 1, 200 pcs", "6. Bolt, 0 pcs", "7. Bolt, -12 pcs", "8. Bolt, 1.200 pcs"]:
            with self.subTest(source=source):
                self.assertIsNone(literal_quantity(source))

    def test_table_columns_are_read_by_name(self):
        first=literal_quantity("1 | Cable | 350 | m | 2.5mm2","Line | Description | Quantity | Unit | Specification")
        reordered=literal_quantity("1 | m | 2.5mm2 | 350 | Cable","Line | Unit | Specification | Quantity | Description")
        self.assertEqual((first["quantity"],first["unit"]),(350,"m"))
        self.assertEqual((reordered["quantity"],reordered["unit"]),(350,"m"))
        self.assertIsNone(literal_quantity("1 | Cable | TBC | m","Line | Description | Quantity | Unit"))
        self.assertIsNone(literal_quantity("1 | Cable | 350 | m","Line | Description | Qty | Qty"))

    def test_header_context_changes_at_the_next_table(self):
        source="Line | Description | Quantity | Unit\n1 | Cable | 350 | m\nSheet: Two\nLine | Unit | Quantity | Description\n1 | pcs | 12 | Bolt\n"
        headers=table_headers(source)
        self.assertEqual(len(headers),2)
        self.assertIn("Description | Quantity",header_before(headers,source.index("1 | Cable")))
        self.assertIn("Unit | Quantity",header_before(headers,source.index("1 | pcs")))
