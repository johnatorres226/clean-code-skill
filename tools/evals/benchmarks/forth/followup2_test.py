import unittest
from forth import evaluate, StackUnderflowError
class Step2(unittest.TestCase):
    def test_2dup(self): self.assertEqual(evaluate(["1 2 2dup"]), [1, 2, 1, 2])
    def test_2drop(self): self.assertEqual(evaluate(["1 2 3 2DROP"]), [1])
    def test_2dup_underflow(self):
        with self.assertRaises(StackUnderflowError): evaluate(["1 2dup"])
    def test_redefine_2drop(self): self.assertEqual(evaluate([": 2drop drop ;", "1 2 2drop"]), [1])
