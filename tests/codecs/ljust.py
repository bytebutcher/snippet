import unittest

from tests.main import new_snippet


class TestLjustCodec(unittest.TestCase):

    def testLjust(self):
        self.assertEqual(new_snippet("<arg1|ljust:'5'>", ["arg1=AB"]), ["AB   "])
