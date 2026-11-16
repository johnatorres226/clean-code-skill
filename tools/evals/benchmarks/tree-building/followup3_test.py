import unittest
from tree_building import Record, BuildTree, ancestors
class Step3(unittest.TestCase):
    def test_tuples(self): self.assertEqual(BuildTree([(0, 0), (1, 0)]).children[0].node_id, 1)
    def test_mixed(self): self.assertEqual(ancestors(BuildTree([(0, 0), Record(1, 0), (2, 1)]), 2), [0, 1, 2])
    def test_tuple_validation(self):
        with self.assertRaises(ValueError): BuildTree([(0, 0), (2, 0)])
