import unittest

from tests.main import new_snippet


class TestTruncatewordsCodec(unittest.TestCase):

    def testTruncatewords(self):
        self.assertEqual(new_snippet("<arg1|truncatewords:'2'>", ["arg1=Good News Everyone!"]), ["Good News"])
