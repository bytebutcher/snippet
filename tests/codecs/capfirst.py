import unittest

from tests.main import new_snippet


class TestCapfirstCodec(unittest.TestCase):

    def testCapfirst(self):
        self.assertEqual(new_snippet("<arg1|capfirst>", ["arg1=hello, world!"]), ["Hello, world!"])

    def testCapfirstNoChar(self):
        self.assertEqual(new_snippet("<arg1|capfirst>", ["arg1=."]), ["."])