import unittest
from tree_building import Record, BuildTree, subtree_size
def tree(): return BuildTree([Record(0, 0), Record(1, 0), Record(2, 0), Record(3, 1), Record(4, 3)])
class Step2(unittest.TestCase):
    def test_root(self): self.assertEqual(subtree_size(tree(), 0), 5)
    def test_branch(self): self.assertEqual(subtree_size(tree(), 1), 3)
    def test_leaf(self): self.assertEqual(subtree_size(tree(), 2), 1)
    def test_unknown(self):
        with self.assertRaises(ValueError): subtree_size(tree(), 9)
