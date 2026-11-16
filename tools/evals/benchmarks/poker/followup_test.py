import unittest
from poker import hand_category
class FollowUp(unittest.TestCase):
    def test_categories(self):
        cases = {
            "4S 5H 7D 8C JS": "high card", "4S 4H 7D 8C JS": "one pair", "4S 4H 7D 7C JS": "two pair",
            "4S 4H 4D 8C JS": "three of a kind", "4S 5H 6D 7C 8S": "straight", "AS 2H 3D 4C 5S": "straight",
            "10D JH QS KD AC": "straight", "2S 4S 7S 9S JS": "flush", "4S 4H 4D 8C 8S": "full house",
            "4S 4H 4D 4C JS": "four of a kind", "4S 5S 6S 7S 8S": "straight flush",
        }
        for hand, expected in cases.items():
            with self.subTest(hand=hand): self.assertEqual(hand_category(hand), expected)
