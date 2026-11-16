import unittest
from book_store import total_with_breakdown
class Step2(unittest.TestCase):
    def test_two_fours(self): self.assertEqual(total_with_breakdown([1, 1, 2, 2, 3, 3, 4, 5]), (5120, [4, 4]))
    def test_six(self): self.assertEqual(total_with_breakdown([1, 2, 3, 4, 5, 6]), (3360, [6]))
    def test_six_plus_one(self): self.assertEqual(total_with_breakdown([1, 1, 2, 3, 4, 5, 6]), (4160, [6, 1]))
    def test_empty(self): self.assertEqual(total_with_breakdown([]), (0, []))
