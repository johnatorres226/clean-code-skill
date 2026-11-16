import unittest
from markdown import parse
class Step3(unittest.TestCase):
    def test_code(self): self.assertEqual(parse("Use `run()` now"), "<p>Use <code>run()</code> now</p>")
    def test_no_italic_inside(self): self.assertEqual(parse("Call `x_y_z` here"), "<p>Call <code>x_y_z</code> here</p>")
    def test_no_bold_inside(self): self.assertEqual(parse("`__init__` and __b__"), "<p><code>__init__</code> and <strong>b</strong></p>")
    def test_in_list(self): self.assertEqual(parse("* `a`"), "<ul><li><code>a</code></li></ul>")
