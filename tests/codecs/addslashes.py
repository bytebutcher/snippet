import unittest

from tests.main import new_snippet


class TestAddSlashesCodec(unittest.TestCase):

    def testAddSlashes(self):
        self.assertEqual(new_snippet("<arg1|addslashes>", ["arg1=I'm using Snippet"]), ["I\\'m using Snippet"])