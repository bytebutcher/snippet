import unittest

from tests.main import new_snippet


class TestLastCodec(unittest.TestCase):

    def testLast(self):
        self.assertEqual(new_snippet("<arg1|last>", ["arg1=test"]), ["test"])

    def testLastRepeatable(self):
        self.assertEqual(new_snippet("<arg1...|last>", ["arg1=test", "arg1=abc"]), ["abc"])
