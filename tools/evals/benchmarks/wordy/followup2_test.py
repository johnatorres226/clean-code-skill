import unittest
from wordy import answer
class Step2(unittest.TestCase):
    def test_squared(self): self.assertEqual(answer("What is 3 squared?"), 9)
    def test_cubed(self): self.assertEqual(answer("What is 2 cubed?"), 8)
    def test_cubed_plus(self): self.assertEqual(answer("What is 2 cubed plus 1?"), 9)
    def test_plus_squared(self): self.assertEqual(answer("What is 1 plus 2 squared?"), 9)
