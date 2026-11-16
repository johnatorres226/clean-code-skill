import unittest
from markdown import parse
class FollowUp(unittest.TestCase):
    def test_paragraph(self): self.assertEqual(parse("This is ~~old~~ text"), "<p>This is <s>old</s> text</p>")
    def test_header(self): self.assertEqual(parse("# ~~Gone~~"), "<h1><s>Gone</s></h1>")
    def test_list_item(self): self.assertEqual(parse("* ~~done~~\n* todo"), "<ul><li><s>done</s></li><li>todo</li></ul>")
    def test_with_bold(self): self.assertEqual(parse("__bold__ and ~~struck~~"), "<p><strong>bold</strong> and <s>struck</s></p>")
