import unittest

from tests.main import new_snippet


class TestJoinCodec(unittest.TestCase):

    def testJoinRepeatable(self):
        self.assertEqual(new_snippet("<arg1...|join:','>", ["arg1=123", "arg1=456"]), ["123,456"])

    def testJoinNonRepeatable(self):
        self.assertEqual(new_snippet("<arg1|join:','>", ["arg1=123"]), ["123"])
