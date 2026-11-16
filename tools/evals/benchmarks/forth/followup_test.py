import unittest
from forth import evaluate, StackUnderflowError
class FollowUp(unittest.TestCase):
    def test_rot(self): self.assertEqual(evaluate(["1 2 3 rot"]), [2, 3, 1])
    def test_rot_case_insensitive(self): self.assertEqual(evaluate(["1 2 3 ROT"]), [2, 3, 1])
    def test_nip(self): self.assertEqual(evaluate(["1 2 nip"]), [2])
    def test_rot_underflow(self):
        with self.assertRaises(StackUnderflowError): evaluate(["1 2 rot"])
    def test_nip_underflow(self):
        with self.assertRaises(StackUnderflowError): evaluate(["1 nip"])
    def test_user_can_redefine_rot(self): self.assertEqual(evaluate([": rot swap ;", "1 2 rot"]), [2, 1])
