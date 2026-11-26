import unittest
from markdown import parse
class Step2(unittest.TestCase):
    def test_ordered(self): self.assertEqual(parse("1. one\n2. two"), "<ol><li>one</li><li>two</li></ol>")
    def test_ordered_inline(self): self.assertEqual(parse("1. __bold__"), "<ol><li><strong>bold</strong></li></ol>")
    def test_header_then_ordered(self): self.assertEqual(parse("# H\n1. a"), "<h1>H</h1><ol><li>a</li></ol>")
    def test_unordered_unchanged(self): self.assertEqual(parse("* a\n* b"), "<ul><li>a</li><li>b</li></ul>")
