import unittest

from tests.main import new_snippet


class TestFirstCodec(unittest.TestCase):

    def testFirst(self):
        self.assertEqual(new_snippet("<arg1|first>", ["arg1=test"]), ["test"])

    def testFirstRepeatable(self):
        self.assertEqual(new_snippet("<arg1...|first>", ["arg1=test", "arg1=abc"]), ["test"])
