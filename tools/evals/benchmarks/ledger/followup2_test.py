import unittest
from ledger import format_entries, create_entry
H_US = "Date       | Description               | Change       "
class Step2(unittest.TestCase):
    def test_title_empty(self): self.assertEqual(format_entries("USD", "en_US", [], title="Q1"), "Q1\n" + H_US)
    def test_title_with_entry(self):
        e = [create_entry("2015-01-01", "Buy present", -1000)]
        self.assertEqual(format_entries("USD", "en_US", e, title="Gifts"),
                         "Gifts\n" + H_US + "\n01/01/2015 | Buy present               |      ($10.00)")
    def test_no_title_unchanged(self): self.assertEqual(format_entries("USD", "en_US", []), H_US)
