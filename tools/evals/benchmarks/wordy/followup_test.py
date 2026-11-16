import unittest
from wordy import answer
class FollowUp(unittest.TestCase):
    def test_power(self): self.assertEqual(answer("What is 2 raised to the 3rd power?"), 8)
    def test_first_power(self): self.assertEqual(answer("What is 3 raised to the 1st power?"), 3)
    def test_power_then_plus(self): self.assertEqual(answer("What is 2 raised to the 5th power plus 1?"), 33)
    def test_negative_base(self): self.assertEqual(answer("What is -2 raised to the 2nd power?"), 4)
    def test_missing_exponent(self):
        with self.assertRaises(ValueError): answer("What is 2 raised to the power?")
