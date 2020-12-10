import unittest

from tests.main import new_snippet


class TestSha512Codec(unittest.TestCase):

    def testSha512(self):
        self.assertEqual(new_snippet("<arg1|sha512>", ["arg1=abcdefghijklmnopqrstuvwxyz"]),
                         ["4dbff86cc2ca1bae1e16468a05cb9881c97f1753bce"
                          "3619034898faa1aabe429955a1bf8ec483d7421fe3c"
                          "1646613a59ed5441fb0f321389f77f48a879c7b1f1"])
