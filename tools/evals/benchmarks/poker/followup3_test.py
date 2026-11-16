import unittest
from poker import best_hands, hand_category
class Step3(unittest.TestCase):
    def test_four_cards(self):
        with self.assertRaises(ValueError): best_hands(["4S 5S 7H 8D"])
    def test_bad_rank(self):
        with self.assertRaises(ValueError): best_hands(["4S 5S 7H 8D 1C"])
    def test_bad_suit(self):
        with self.assertRaises(ValueError): hand_category("4S 5S 7H 8D 9X")
