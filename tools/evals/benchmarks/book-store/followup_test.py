import unittest
from book_store import total
class FollowUp(unittest.TestCase):
    def test_single_sixth_book(self): self.assertEqual(total([6]), 800)
    def test_six_different_books(self): self.assertEqual(total([1, 2, 3, 4, 5, 6]), 3360)
    def test_six_set_plus_one(self): self.assertEqual(total([1, 1, 2, 3, 4, 5, 6]), 4160)
    def test_ten_books_with_sixth(self): self.assertEqual(total([1, 1, 2, 2, 3, 3, 4, 5, 6, 6]), 5920)
    def test_two_sixth_books(self): self.assertEqual(total([6, 6]), 1600)
