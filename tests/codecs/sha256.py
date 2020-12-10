import unittest

from tests.main import new_snippet


class TestSha256Codec(unittest.TestCase):

    def testSha256(self):
        self.assertEqual(new_snippet("<arg1|sha256>", ["arg1=abcdefghijklmnopqrstuvwxyz"]),
                         ["71c480df93d6ae2f1efad1447c66c9525e316218cf51fc8d9ed832f2daf18b73"])
