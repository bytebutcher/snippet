import unittest

from tests.main import new_snippet


class TestDquoteCodec(unittest.TestCase):

    def testDquote(self):
        self.assertEqual(new_snippet("<arg1|dquote>", ["arg1=test"]), ["\"test\""])
