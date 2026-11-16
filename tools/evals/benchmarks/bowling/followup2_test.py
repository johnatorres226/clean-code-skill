import unittest
from bowling import BowlingGame
def game(rolls):
    g = BowlingGame()
    for r in rolls: g.roll(r)
    return g
class Step2(unittest.TestCase):
    def test_new_game(self): self.assertFalse(game([]).is_complete())
    def test_open_game(self): self.assertTrue(game([3, 4] * 10).is_complete())
    def test_perfect_game(self): self.assertTrue(game([10] * 12).is_complete())
    def test_missing_bonus(self): self.assertFalse(game([10] * 11).is_complete())
    def test_tenth_spare_needs_fill(self): self.assertFalse(game([0, 0] * 9 + [5, 5]).is_complete())
