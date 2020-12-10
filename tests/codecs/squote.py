import unittest

from tests.main import new_snippet


class TestSquoteCodec(unittest.TestCase):

    def testSquote(self):
        self.assertEqual(new_snippet("<arg1|squote>", ["arg1=test"]), ["'test'"])
