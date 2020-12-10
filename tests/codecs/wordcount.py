import unittest

from tests.main import new_snippet


class TestWordcountCodec(unittest.TestCase):

    def testWordcount(self):
        self.assertEqual(new_snippet("<arg1|wordcount>", ["arg1=Good News Everyone!"]), ["3"])
