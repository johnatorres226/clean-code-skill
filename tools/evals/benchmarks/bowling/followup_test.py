import unittest
from bowling import BowlingGame
def game(rolls):
    g = BowlingGame()
    for r in rolls: g.roll(r)
    return g
class FollowUp(unittest.TestCase):
    def test_open_frame(self): self.assertEqual(game([3, 4]).frame_scores(), [7])
    def test_pending_strike(self): self.assertEqual(game([10]).frame_scores(), [])
    def test_strike_then_open(self): self.assertEqual(game([10, 3, 4]).frame_scores(), [17, 24])
    def test_pending_spare(self): self.assertEqual(game([5, 5]).frame_scores(), [])
    def test_spare_then_partial(self): self.assertEqual(game([5, 5, 3]).frame_scores(), [13])
    def test_three_strikes(self): self.assertEqual(game([10, 10, 10]).frame_scores(), [30])
    def test_perfect_game(self): self.assertEqual(game([10] * 12).frame_scores(), list(range(30, 301, 30)))
    def test_all_open(self): self.assertEqual(game([3, 4] * 10).frame_scores(), list(range(7, 71, 7)))
