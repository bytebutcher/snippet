import unittest

from tests.main import new_snippet


class TestUpperCodec(unittest.TestCase):

    def testUpper(self):
        self.assertEqual(new_snippet("<arg1|upper>", ["arg1=test"]), ["TEST"])
