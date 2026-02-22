import unittest

from tests.main import new_snippet


class TestBasenameCodec(unittest.TestCase):

    def testBasename(self):
        self.assertEqual(new_snippet("<arg1...|basename>", ['arg1=/path/to/foo', '/path/to/bar']), [
            'foo bar'
        ])
