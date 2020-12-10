import unittest

from tests.main import new_snippet


class TestDateCodec(unittest.TestCase):

    def testDate(self):
        self.assertEqual(new_snippet("<arg1|date:'%Y/%m/%d'>", ["arg1=1607038029"]), ["2020/12/04"])
