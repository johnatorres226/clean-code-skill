import unittest
from ledger import format_entries, create_entry
H_US = "Date       | Description               | Change       "
H_NL = "Datum      | Omschrijving              | Verandering  "
class FollowUp(unittest.TestCase):
    def test_gbp_us_negative(self):
        e = [create_entry("2015-01-01", "Buy present", -1000)]
        self.assertEqual(format_entries("GBP", "en_US", e), H_US + "\n01/01/2015 | Buy present               |      (£10.00)")
    def test_gbp_us_positive_thousands(self):
        e = [create_entry("2015-03-12", "Buy present", 123456)]
        self.assertEqual(format_entries("GBP", "en_US", e), H_US + "\n03/12/2015 | Buy present               |    £1,234.56 ")
    def test_gbp_nl_positive(self):
        e = [create_entry("2015-03-12", "Buy present", 123456)]
        self.assertEqual(format_entries("GBP", "nl_NL", e), H_NL + "\n12-03-2015 | Buy present               |   £ 1.234,56 ")
    def test_gbp_nl_negative(self):
        e = [create_entry("2015-03-12", "Buy present", -12345)]
        self.assertEqual(format_entries("GBP", "nl_NL", e), H_NL + "\n12-03-2015 | Buy present               |    £ -123,45 ")
