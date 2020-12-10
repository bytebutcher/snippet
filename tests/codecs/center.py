import unittest

from tests.main import new_snippet


class TestCenterCodec(unittest.TestCase):

    def testCenter(self):
        self.assertEqual(new_snippet("<arg1|center:'10'>", ["arg1=AB"]), ["    AB    "])
