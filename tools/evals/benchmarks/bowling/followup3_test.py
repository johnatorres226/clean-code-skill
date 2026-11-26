import unittest
from bowling import BowlingGame
def game(rolls, frames):
    g = BowlingGame(frames=frames)
    for r in rolls: g.roll(r)
    return g
class Step3(unittest.TestCase):
    def test_five_frame_perfect(self): self.assertEqual(game([10] * 7, 5).score(), 150)
    def test_five_frame_scores(self): self.assertEqual(game([10] * 7, 5).frame_scores(), [30, 60, 90, 120, 150])
    def test_five_frame_open(self): self.assertEqual(game([3, 4] * 5, 5).score(), 35)
    def test_five_frame_complete(self): self.assertTrue(game([3, 4] * 5, 5).is_complete())
    def test_default_unchanged(self):
        g = BowlingGame()
        for r in [3, 4] * 10: g.roll(r)
        self.assertEqual(g.score(), 70)
