import unittest

from tests.main import new_snippet


class TestRjustCodec(unittest.TestCase):

    def testRjust(self):
        self.assertEqual(new_snippet("<arg1|rjust:'5'>", ["arg1=AB"]), ["   AB"])
