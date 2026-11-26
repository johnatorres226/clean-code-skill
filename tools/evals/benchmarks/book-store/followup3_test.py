import unittest
from book_store import total, total_with_breakdown
class Step3(unittest.TestCase):
    def test_zero(self):
        with self.assertRaises(ValueError): total([0])
    def test_seven(self):
        with self.assertRaises(ValueError): total([1, 7])
    def test_breakdown_validates(self):
        with self.assertRaises(ValueError): total_with_breakdown([9])
