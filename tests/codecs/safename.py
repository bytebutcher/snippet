import unittest

from tests.main import new_snippet


class TestSafenameCodec(unittest.TestCase):

    def testSafename(self):
        self.assertEqual(new_snippet("<arg1|safename>", ["arg1=some $string$"]), ["some__string_"])
