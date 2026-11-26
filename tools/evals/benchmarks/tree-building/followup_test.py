import unittest
from tree_building import Record, BuildTree, ancestors
def tree(): return BuildTree([Record(0, 0), Record(1, 0), Record(2, 0), Record(3, 1), Record(4, 3)])
class FollowUp(unittest.TestCase):
    def test_root(self): self.assertEqual(ancestors(tree(), 0), [0])
    def test_child(self): self.assertEqual(ancestors(tree(), 2), [0, 2])
    def test_deep(self): self.assertEqual(ancestors(tree(), 4), [0, 1, 3, 4])
    def test_unknown(self):
        with self.assertRaises(ValueError): ancestors(tree(), 9)
