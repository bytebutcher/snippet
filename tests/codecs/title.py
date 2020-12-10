import unittest

from tests.main import new_snippet


class TestTitleCodec(unittest.TestCase):

    def testTitle(self):
        self.assertEqual(new_snippet("<arg1|title>", ["arg1=hello, world!"]), ["Hello, World!"])

    def testTitleEmptyString(self):
        self.assertEqual(new_snippet("<arg1|title>", ["arg1="]), [""])