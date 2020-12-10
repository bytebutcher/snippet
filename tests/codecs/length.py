import unittest

from tests.main import new_snippet


class TestLengthCodec(unittest.TestCase):

    def testLength(self):
        self.assertEqual(new_snippet("<arg1|length>", ["arg1=test"]), ["4"])
        self.assertEqual(new_snippet("<arg1|length>", ["arg1=test", "arg1=tset"]), ["4", "4"])

    def testLengthRepeatable(self):
        self.assertEqual(new_snippet("<arg1...|length>", ["arg1=test", "arg1=abc"]), ["2"])
