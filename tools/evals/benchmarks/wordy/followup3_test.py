import unittest
from wordy import answer
class Step3(unittest.TestCase):
    def test_thousands(self): self.assertEqual(answer("What is 1,000 plus 1?"), 1001)
    def test_millions(self): self.assertEqual(answer("What is 1,000,000 minus 1?"), 999999)
    def test_negative(self): self.assertEqual(answer("What is -1,500 plus 500?"), -1000)
    def test_still_rejects(self):
        with self.assertRaises(ValueError): answer("What is 1 plus plus 2?")
