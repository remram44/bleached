from bleached import UnsafeInput, check_html
import unittest


class TestBleached(unittest.TestCase):
    def check(self, source):
        check_html(
            source,
            tags=['p', 'br', 'code',
                  'a', 'img',
                  'b', 'u',
              ],
            attributes={'a': ['href', 'title'], 'img': ['src']},
        )

    def bad(self, source, message, index, line, line_position):
        with self.assertRaises(UnsafeInput) as e:
            self.check(source)
        self.assertEqual(e.exception.message, message)
        self.assertEqual(e.exception.index, index)
        self.assertEqual(e.exception.line, line)
        self.assertEqual(e.exception.line_position, line_position)

    def test_check(self):
        self.check('<p>Hello <b>world</b></p>')

        self.bad(
            '<p style="color: red;">Hello</p>',
            "Forbidden attribute 'style' in tag 'p'",
            8, 1, 9,
        )

        self.check('<p><a href="somewhere" title="Click!">Hello</a></p>')

        self.bad(
            '<p>\n<a/>\n</p>',
            "Self-closing tag for non-void element 'a'",
            8, 2, 5,
        )

        self.check('<p><br/></p>')
        self.check('<p><br></p>')

        self.bad(
            '<p>',
            "Missing closing tag for element 'p'",
            3, 1, 4,
        )

        self.bad(
            '</p>',
            "Closing tag for wrong element 'p'",
            4, 1, 5,
        )
        self.bad(
            '<p><a></p>',
            "Closing tag for wrong element 'p'",
            10, 1, 11,
        )

        self.bad(
            '<a href>hello</a>',
            "Unexpected character '>' in attribute",
            8, 1, 9,
        )


if __name__ == '__main__':
    unittest.main()
