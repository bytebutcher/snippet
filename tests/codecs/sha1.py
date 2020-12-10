import unittest

from tests.main import new_snippet


class TestSha1Codec(unittest.TestCase):

    def testSha1(self):
        self.assertEqual(new_snippet("<arg1|sha1>", ["arg1=abcdefghijklmnopqrstuvwxyz"]),
                         ["32d10c7b8cf96570ca04ce37f2a19d84240d3a89"])
