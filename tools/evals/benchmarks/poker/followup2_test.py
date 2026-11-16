import unittest
from poker import best_hands, hand_category
class Step2(unittest.TestCase):
    def test_lowercase(self): self.assertEqual(best_hands(["4s 5h 6d 7c 8s", "2S 2H 3D 4C 9S"]), ["4s 5h 6d 7c 8s"])
    def test_extra_spaces(self): self.assertEqual(best_hands(["4S  5H 6D   7C 8S"]), ["4S  5H 6D   7C 8S"])
    def test_category_lowercase(self): self.assertEqual(hand_category("4s 4h 4d 8c 8s"), "full house")
