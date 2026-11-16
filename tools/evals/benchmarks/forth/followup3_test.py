import unittest
from forth import evaluate, StackUnderflowError
class Step3(unittest.TestCase):
    def test_dup_from_stack(self): self.assertEqual(evaluate(["dup"], stack=[5]), [5, 5])
    def test_add_from_stack(self): self.assertEqual(evaluate(["+"], stack=[1, 2]), [3])
    def test_rot_from_stack(self): self.assertEqual(evaluate(["rot"], stack=[1, 2, 3]), [2, 3, 1])
    def test_underflow_with_stack(self):
        with self.assertRaises(StackUnderflowError): evaluate(["+"], stack=[1])
    def test_default(self): self.assertEqual(evaluate(["1 2 +"]), [3])
