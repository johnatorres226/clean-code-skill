import unittest
from ledger import format_entries, create_entry
class Step3(unittest.TestCase):
    def test_bad_date(self):
        with self.assertRaises(ValueError): create_entry("2015/01/01", "x", 100)
    def test_unknown_currency(self):
        with self.assertRaises(ValueError): format_entries("JPY", "en_US", [])
    def test_unknown_locale(self):
        with self.assertRaises(ValueError): format_entries("USD", "fr_FR", [])
    def test_gbp_still_valid(self): format_entries("GBP", "nl_NL", [])
