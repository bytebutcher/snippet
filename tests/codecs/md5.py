import unittest

from tests.main import new_snippet


class TestMd5Codec(unittest.TestCase):

    def testMd5(self):
        self.assertEqual(new_snippet("<arg1|md5>", ["arg1=abcdefghijklmnopqrstuvwxyz"]),
                         ["c3fcd3d76192e4007dfb496cca67e13b"])
