import unittest

from tests.main import new_snippet


class TestTruncatecharsCodec(unittest.TestCase):

    def testTruncatechars(self):
        self.assertEqual(new_snippet("<arg1|truncatechars:'5'>", ["arg1=Hello, World!"]), ["Hello"])
